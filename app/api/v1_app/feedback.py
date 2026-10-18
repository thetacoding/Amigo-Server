# app/api/v1_app/feedback.py
import json
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from loguru import logger

from app.schemas.base import (
    ResponseModel,
    SessionInfo,
    UserInfo,
    DeviceInfo,
    AppBaseInfo,
    SystemSetting,
)

router = APIRouter()

# 点踩时可选的问题类型（id 稳定供端侧提交；label 供端侧展示）
# 同步通过 assets 接口（/all、/config）下发，端侧无需单独请求反馈模块
FEEDBACK_DISLIKE_ISSUE_TYPES: list[dict[str, str]] = [
    {"id": "incorrect_fact", "label": "事实错误 / 信息不准确"},
    {"id": "irrelevant", "label": "答非所问 / 与问题不相关"},
    {"id": "incomplete", "label": "回答不完整"},
    {"id": "harmful_or_sensitive", "label": "有害、不当或敏感内容"},
    {"id": "format_or_readability", "label": "格式混乱 / 难以理解"},
    {"id": "too_slow", "label": "响应过慢"},
    {"id": "other", "label": "其他"},
]

# 并入 assets 响应中的结构：data.feedback.dislike_issue_types
FEEDBACK_ASSETS_PAYLOAD: dict[str, list[dict[str, str]]] = {
    "dislike_issue_types": FEEDBACK_DISLIKE_ISSUE_TYPES,
}


class FeedbackSubmitRequest(BaseModel):
    """端侧对 Agent 回答、任务结果等提交的反馈。"""

    sessionInfo: SessionInfo
    userInfo: UserInfo
    DeviceInfo: DeviceInfo
    AppBaseInfo: AppBaseInfo
    SystemSetting: SystemSetting

    target_type: Literal["chat_response", "task_result", "other"] = Field(
        default="chat_response",
        description="反馈所针对的结果类型，便于后续扩展",
    )
    target_ref: Optional[str] = Field(
        default=None,
        description="可选：端侧用于关联的业务标识，如消息 id、任务 id",
    )
    rating: Literal["like", "dislike", "none"] = Field(
        ...,
        description="like=赞，dislike=踩，none=撤销对该目标的赞/踩（端侧再次点击同一状态时使用）",
    )
    issue_types: Optional[list[str]] = Field(
        default=None,
        description="点踩时可选：问题类型 id 列表（云侧不强校验，建议与 assets 中 dislike_issue_types 对齐）",
    )
    detail: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="可选：用户补充说明，点踩或撤销时均可按需携带",
    )


@router.post("/submit", response_model=ResponseModel)
async def submit_feedback(req: FeedbackSubmitRequest):
    """
    提交反馈：like / dislike / none（撤销）；issue_types 仅作记录参考，不做枚举强校验。
    当前无持久化，完整请求体会写入应用日志（与 chat 接口一致的 loguru 文件输出）。
    """
    payload = req.model_dump(mode="json")
    logger.info(f"[Feedback] {json.dumps(payload, ensure_ascii=False)}")
    return ResponseModel(
        data={
            "received": True,
            "rating": req.rating,
            "target_type": req.target_type,
        }
    )
