# app/api/v1/chat.py
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from app.schemas.base import ResponseModel, SessionInfo, UserInfo, DeviceInfo, AppBaseInfo, SystemSetting, ChunkEvent, SseChunk, ChunkMeta
from typing import List, Optional, Literal, Any

from app.services.ai.llm.factory import LLMFactory
from app.services.config_service import ConfigService
from app.services.unified_router.capabilities.web_search import get_unified_web_search_service
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from loguru import logger

# 与 unified_router Web Search 适配器 provider_id 一致；不填则走云端 presets 中的 provider_priority
WebSearchProviderId = Literal["tavily", "baidu", "volcengine"]

router = APIRouter()


def _extract_latest_user_query(messages: List["Message"]) -> str:
    return next(
        (m.content.strip() for m in reversed(messages) if m.role == "user" and m.content and m.content.strip()),
        "",
    )


def _build_cloud_system_prompt(
    req: "ChatRequest",
    latest_user_query: str,
    web_search_payload: Optional[dict],
    template_id: str = "default_cloud_prompt",
) -> str:
    """
    云侧系统模板：拼接端侧 systemPrompt、历史会话、检索结果、当前时间、用户query。
    """
    current_time = datetime.now(timezone.utc).isoformat()
    history_lines = [
        f"{m.role}: {m.content}" for m in req.messages if m.content and m.content.strip()
    ]
    history_text = "\n".join(history_lines) if history_lines else "(empty)"
    web_search_text = json.dumps(web_search_payload, ensure_ascii=False) if web_search_payload else "(none)"
    client_system_prompt = (req.options.systemPrompt or "").strip() or "(none)"

    template_cfg = ConfigService.get_prompt_template(template_id=template_id)
    template = template_cfg.get("template")

    if not template:
        return ""

    return template.format(
        client_system_prompt=client_system_prompt,
        current_time=current_time,
        latest_user_query=latest_user_query or "(empty)",
        history_text=history_text,
        web_search_text=web_search_text,
    )

class Message(BaseModel):
    """消息模型"""
    role: str = Field(..., description="角色: user, assistant, 或 system")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="发送者姓名（群组模式下区分不同用户）")

class Option(BaseModel):
    """选项模型"""
    systemPrompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[str] = None
    request_llm: Optional[bool] = True
    cloud_prompt_template_id: Optional[str] = "default_cloud_prompt"
    web_search_enabled: Optional[bool] = True
    web_search_format: Optional[Literal["markdown", "blocks", "both"]] = "both"
    web_search_max_results: Optional[int] = None
    web_search_content_max_len: Optional[int] = 280
    # 单次请求优先哪个供应商；不填则完全按云端 app_config.web_search.provider_priority
    web_search_preferred_provider: Optional[WebSearchProviderId] = None
    # True 时仅尝试 preferred，失败不回落链路上其它供应商
    web_search_strict_preferred: Optional[bool] = False

class ChatRequest(BaseModel):
    """聊天请求模型"""
    sessionInfo: SessionInfo
    userInfo: UserInfo
    DeviceInfo: DeviceInfo
    AppBaseInfo: AppBaseInfo
    SystemSetting: SystemSetting
    # 改为 messages 列表，支持多轮历史记录直接透传
    messages: List[Message]
    provider: Optional[str] = None
    model: Optional[str] = None
    streaming: Optional[bool] = True
    reasoning: Optional[bool] = False
    # 调教参数
    options: Option


async def _build_web_search_payload(
    req: "ChatRequest", latest_user_query: str
) -> Optional[dict]:
    if not req.options.web_search_enabled or not latest_user_query:
        return None

    logger.info(f"[Chat] Web Search Enabled: {latest_user_query}")
    search_service = get_unified_web_search_service()
    raw_result = await search_service.asearch(
        latest_user_query,
        max_results=req.options.web_search_max_results,
        preferred_provider=req.options.web_search_preferred_provider,
        strict_preferred=bool(req.options.web_search_strict_preferred),
    )
    logger.info(f"[Chat] Web Search Result: {raw_result}")

    content_max_len = req.options.web_search_content_max_len or 280
    blocks = search_service.to_readable_blocks(raw_result, content_max_len=content_max_len)
    markdown = search_service.to_markdown(raw_result, content_max_len=content_max_len)
    result_count = len(blocks.get("results") or [])
    payload = {
        "query": latest_user_query,
        "result_count": result_count,
        "request_id": blocks.get("request_id"),
        "provider": blocks.get("provider"),
    }

    if req.options.web_search_format == "markdown":
        payload["markdown"] = markdown
    elif req.options.web_search_format == "blocks":
        payload["blocks"] = blocks
    else:
        payload["blocks"] = blocks
        payload["markdown"] = markdown

    return payload


async def _build_web_search_payload_by_query(req: "ChatRequest", query: str) -> Optional[dict]:
    """供 agent tool 使用：基于指定 query 执行检索。"""
    if not req.options.web_search_enabled or not query.strip():
        return None
    return await _build_web_search_payload(req, query.strip())


def _split_web_search_sse_fields(web_search_payload: dict) -> tuple[str, dict]:
    """
    Web Search 回传帧:
    - content 优先放 markdown（给用户直接展示）
    - extra.web_search 不携带 markdown（保留结构化元数据）
    """
    payload_without_markdown = dict(web_search_payload)
    markdown = payload_without_markdown.pop("markdown", None)
    return (markdown or "web_search_completed"), payload_without_markdown


def _build_lc_messages(
    req: "ChatRequest",
    latest_user_query: str,
    web_search_payload: Optional[dict],
) -> list:
    """构建 LangChain 消息列表"""
    cloud_system_prompt = _build_cloud_system_prompt(
        req=req,
        latest_user_query=latest_user_query,
        web_search_payload=web_search_payload,
        template_id=req.options.cloud_prompt_template_id or "default_cloud_prompt",
    )
    lc_messages = [SystemMessage(content=cloud_system_prompt)]
    for m in req.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content, name=m.name))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))
        elif m.role == "system":
            # 端侧可能透传了历史 system message，保留但放在云侧 system prompt 之后
            lc_messages.append(SystemMessage(content=m.content))
    return lc_messages


def _build_web_search_agent_system_prompt() -> str:
    return (
        "你是一个可使用 web_search 工具的助手。"
        "请先判断用户问题是否需要联网检索最新事实、实时信息、外部网页内容。"
        "如果是寒暄、闲聊、通用常识、无需实时性的内容，不要调用 web_search。"
        "若调用 web_search，请只传最关键的检索 query。"
    )


async def _run_web_search_agent_if_needed(
    req: "ChatRequest",
    runnable: Any,
    lc_messages: list,
) -> tuple[list, Optional[dict], dict]:
    """
    用 tool-calling 方式让模型自主判断是否需要 web_search。
    返回:
    - 增强后的 lc_messages（若调用了工具，会插入 AI tool_call + ToolMessage）
    - 实际检索结果（若未调用则为 None）
    - query 理解信息（供端侧 step 展示）
    """
    latest_user_query = _extract_latest_user_query(req.messages)
    if not req.options.web_search_enabled or not latest_user_query:
        return lc_messages, None, {
            "need_web_search": False,
            "reason": "web_search_disabled_or_empty_query",
            "query": latest_user_query,
        }

    @tool
    async def web_search(query: str) -> str:
        """当问题需要联网检索实时/外部信息时调用。"""
        payload = await _build_web_search_payload_by_query(req, query)
        return json.dumps(payload or {}, ensure_ascii=False)

    agent_runnable = runnable.bind_tools([web_search])
    # 某些供应商（如腾讯）要求 system 必须在消息列表最前，且不接受中间穿插 system。
    # 因此决策阶段只使用 "1 条 system + 1 条最新 user query"。
    decision_messages = [
        SystemMessage(content=_build_web_search_agent_system_prompt()),
        HumanMessage(content=latest_user_query),
    ]
    decision = await agent_runnable.ainvoke(decision_messages)
    if not isinstance(decision, AIMessage):
        return lc_messages, None, {
            "need_web_search": False,
            "reason": "decision_not_ai_message",
            "query": latest_user_query,
        }

    tool_calls = decision.tool_calls or []
    if not tool_calls:
        return lc_messages, None, {
            "need_web_search": False,
            "reason": "agent_decided_no_tool_call",
            "query": latest_user_query,
        }

    web_search_payload: Optional[dict] = None
    appended_messages = [*lc_messages, decision]
    selected_query = latest_user_query
    for tc in tool_calls:
        if tc.get("name") != "web_search":
            continue
        tool_args = tc.get("args") or {}
        search_query = str(tool_args.get("query") or latest_user_query).strip()
        selected_query = search_query or latest_user_query
        web_search_payload = await _build_web_search_payload_by_query(req, search_query)
        tool_call_id = tc.get("id") or f"tool_call_{uuid4().hex}"
        appended_messages.append(
            ToolMessage(
                tool_call_id=tool_call_id,
                name="web_search",
                content=json.dumps(web_search_payload or {}, ensure_ascii=False),
            )
        )

    return appended_messages, web_search_payload, {
        "need_web_search": web_search_payload is not None,
        "reason": "agent_tool_call_web_search",
        "query": latest_user_query,
        "search_query": selected_query,
    }


def _build_runnable(req: "ChatRequest"):
    llm = LLMFactory.get_model(
        provider=req.provider,
        model=req.model,
        streaming=req.streaming,
        reasoning=req.reasoning
    )
    runtime_params = {
        "temperature": req.options.temperature,
        # 如果以后有 top_p 等参数也可以往这里加
    }
    effective_params = {k: v for k, v in runtime_params.items() if v is not None}
    if effective_params:
        runnable = llm.bind(**effective_params)
        # 尽量把底层模型的运行时元信息透传到绑定后的 runnable 上
        for key in ("_runtime_provider", "_runtime_model"):
            value = getattr(llm, key, None)
            if value:
                setattr(runnable, key, value)
        return runnable
    return llm


def _extract_chunk_meta_from_runnable(runnable: Any, req: "ChatRequest") -> ChunkMeta:
    """
    优先从 runnable（包含 bind 包装）提取最终生效的 provider/model。
    如果提取失败，再回退到请求参数，保证兼容。
    """
    current = runnable
    visited = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        provider = getattr(current, "_runtime_provider", None)
        model = getattr(current, "_runtime_model", None)
        if provider and model:
            return ChunkMeta(provider=provider, model=model)
        current = getattr(current, "bound", None)

    return ChunkMeta(
        provider=req.provider or "unknown",
        model=req.model or "unknown",
    )


async def _generate_only_web_search_stream(web_search_payload: Optional[dict]):
    if web_search_payload is not None:
        content, payload_without_markdown = _split_web_search_sse_fields(web_search_payload)
        yield SseChunk(
            event=ChunkEvent.STEP,
            content=content,
            stepId="web_search",
            stepLabel="网页检索",
            extra={"web_search": payload_without_markdown},
        ).to_sse()
    yield SseChunk(event=ChunkEvent.DONE, content="llm_skipped").to_sse()


async def _generate_llm_stream(
    req: ChatRequest,
    runnable: Any,
    lc_messages: list,
    web_search_payload: Optional[dict],
    query_understanding: Optional[dict] = None,
):
    """生成 LLM 流式响应"""
    if query_understanding is not None:
        # 首帧：告知端侧“query 理解/用户需求理解”过程结论。
        need_web_search = bool(query_understanding.get("need_web_search"))
        label = "需要联网检索" if need_web_search else "无需联网检索"
        yield SseChunk(
            event=ChunkEvent.STEP,
            content=label,
            stepId="query_understanding",
            stepLabel="用户需求理解",
            extra={"query_understanding": query_understanding},
        ).to_sse()

    if web_search_payload is not None:
        content, payload_without_markdown = _split_web_search_sse_fields(web_search_payload)
        # 先回传一帧检索结果，端侧可提前渲染“已检索到 N 条”
        yield SseChunk(
            event=ChunkEvent.STEP,
            content=content,
            stepId="web_search",
            stepLabel="网页检索",
            extra={"web_search": payload_without_markdown},
        ).to_sse()

    chunk_meta = _extract_chunk_meta_from_runnable(runnable, req)
    full_reply = ""

    # 使用 astream 逐块获取内容
    async for chunk in runnable.astream(lc_messages):
        # LangChain 的 chunk 对象通常有 content 属性
        content = chunk.content
        sse_chunk = SseChunk(event=ChunkEvent.TEXT, content=chunk.content, meta=chunk_meta)
        if content:
            full_reply += content
            # 严格遵循 SSE 格式: "data: 内容\n\n"
            yield sse_chunk.to_sse()

    # 末帧：完整回答，便于端侧做引用替换、二次处理和最终效果核验。
    yield SseChunk(
        event=ChunkEvent.STEP,
        content=full_reply,
        stepId="final_answer",
        stepLabel="最终回答",
        extra={"full_reply": full_reply},
        meta=chunk_meta,
    ).to_sse()
    yield SseChunk(event=ChunkEvent.DONE, content="completed", meta=chunk_meta).to_sse()


def _build_llm_skipped_response(req: "ChatRequest", web_search_payload: Optional[dict]):
    logger.info("[Chat] Request LLM Skipped")
    if req.streaming:
        return StreamingResponse(
            _generate_only_web_search_stream(web_search_payload),
            media_type="text/event-stream",
        )

    return ResponseModel(
        data={
            "reply": "",
            "llm_skipped": True,
            "web_search": web_search_payload,
        }
    )


async def _build_chat_success_response(
    req: ChatRequest,
    runnable: Any,
    lc_messages: list,
    web_search_payload: Optional[dict],
    query_understanding: Optional[dict] = None,
):
    """构建聊天成功响应"""
    if req.streaming:
        return StreamingResponse(
            _generate_llm_stream(req, runnable, lc_messages, web_search_payload, query_understanding),
            media_type="text/event-stream",
        )

    response = await runnable.ainvoke(lc_messages)
    logger.info(f"[Chat] Non-streaming response: {response.content}")
    data = {"reply": response.content}
    if web_search_payload is not None:
        data["web_search"] = web_search_payload
    return ResponseModel(data=data)


@router.post("/completions")
async def chat_completions(req: ChatRequest):
    """聊天完成"""
    try:
        logger.info(f"[Chat] Request: {req.model_dump_json(exclude_none=True, ensure_ascii=False)}")

        # 1. 先抽取用户最新 query（后续 agent/tool 决策会用）
        latest_user_query = _extract_latest_user_query(req.messages)

        # 2. 先组装基础消息（初始无检索结果）
        lc_messages = _build_lc_messages(req, latest_user_query, None)
        logger.info(f"[Chat] LC Messages: {lc_messages}")

        # 3. 可配置跳过 LLM 调用（沿用原逻辑：若启用则直接检索一次并返回）
        web_search_payload: Optional[dict] = None
        query_understanding: Optional[dict] = None
        if req.options.request_llm is False:
            web_search_payload = await _build_web_search_payload(req, latest_user_query)
            return _build_llm_skipped_response(req, web_search_payload)

        # 4. 获取模型并动态绑定参数
        runnable = _build_runnable(req)

        # 5. 让模型决定是否调用 web_search 工具
        lc_messages, web_search_payload, query_understanding = await _run_web_search_agent_if_needed(
            req=req,
            runnable=runnable,
            lc_messages=lc_messages,
        )

        # 6. 分流返回（流式 / 非流式）
        return await _build_chat_success_response(
            req,
            runnable,
            lc_messages,
            web_search_payload,
            query_understanding=query_understanding,
        )
    except Exception as e:
        logger.exception("[Chat] Error during completion")
        return JSONResponse(
            status_code=500,
            content=ResponseModel(code=500, msg=str(e)).model_dump()
        )