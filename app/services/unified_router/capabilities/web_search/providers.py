"""Web Search 供应商适配器实现。"""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from app.core.config import settings
from ...adapter import BaseCapabilityAdapter
from ...exceptions import ProviderInvokeError, QuotaExhaustedError
from .normalizers import (
    normalize_baidu_response,
    normalize_tavily_response,
    normalize_volcengine_response,
)


def _truncate_qianfan_web_search_query(text: str, max_len: int = 72) -> str:
    """千帆 web_search 单条 content 有长度限制，超出截断（按 Unicode 码位）。"""
    if len(text) <= max_len:
        return text
    return text[:max_len]


def _qianfan_web_search_request(
    query: str,
    *,
    max_results_param: Any,
    default_max_results: int,
    api_key: str,
    api_url: str,
    search_source: str,
    timeout: int,
) -> dict[str, Any]:
    """POST 千帆 ``/v2/ai_search/web_search`` 的公共请求体与鉴权。"""
    max_n = int(max_results_param if max_results_param is not None else default_max_results)
    top_k = min(max(1, max_n), 50)
    content = _truncate_qianfan_web_search_query(query)
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": content}],
        "search_source": search_source,
        "resource_type_filter": [{"type": "web", "top_k": top_k}],
    }
    key = api_key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "X-Appbuilder-Authorization": f"Bearer {key}",
    }
    data = _post_json(url=api_url, payload=payload, headers=headers, timeout=timeout)
    if isinstance(data, dict) and "references" not in data and data.get("code") is not None:
        msg = str(data.get("message") or data.get("code") or "unknown error")
        raise ProviderInvokeError(msg)
    return data


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        if exc.code in (429, 402):
            raise QuotaExhaustedError(f"HTTP {exc.code}: {detail}") from exc
        raise ProviderInvokeError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise ProviderInvokeError(f"网络异常: {exc.reason}") from exc


def _feedcoop_error_message(data: dict[str, Any]) -> str | None:
    """字节 FeedCoop 在 HTTP 200 下用 ResponseMetadata.Error 表示业务错误。"""
    meta = data.get("ResponseMetadata")
    if not isinstance(meta, dict):
        return None
    err = meta.get("Error")
    if not err or not isinstance(err, dict):
        return None
    msg = err.get("Message")
    code = err.get("Code")
    if msg:
        return str(msg)
    if code is not None:
        return str(code)
    if err.get("CodeN") is not None:
        return f"code={err.get('CodeN')}"
    return "unknown Error"


def _feedcoop_web_search_request(
    query: str,
    *,
    max_results_param: Any,
    default_max_results: int,
    api_key: str,
    api_url: str,
    timeout: int,
    search_type: str,
    need_content: bool,
    need_summary: bool,
) -> dict[str, Any]:
    """
    字节系 ``open.feedcoopapi.com`` /search_api/web_search。

    参考：社区示例里使用 ``Query`` / ``SearchType`` / ``Count`` / ``Filter`` / ``NeedSummary`` 等字段。
    """
    max_n = int(max_results_param if max_results_param is not None else default_max_results)
    count = min(max(1, max_n), 50)
    payload: dict[str, Any] = {
        "Query": query,
        "SearchType": search_type,
        "Count": count,
        "Filter": {
            "NeedContent": need_content,
            "NeedUrl": True,
        },
        "NeedSummary": need_summary,
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {api_key}",
    }
    return _post_json(url=api_url, payload=payload, headers=headers, timeout=timeout)


class TavilyWebSearchAdapter(BaseCapabilityAdapter):
    """Tavily 网页检索适配器。"""

    def __init__(self) -> None:
        super().__init__(provider_id="tavily")

    def supported_capabilities(self) -> frozenset[str]:
        """声明支持的能力集合。"""
        return frozenset({"web_search"})

    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        """将 Tavily 原始响应转换为统一结构。"""
        return normalize_tavily_response(self.provider_id, query, raw_response).to_payload()

    async def invoke(self, capability_id: str, **params: Any) -> dict[str, Any]:
        """调用 Tavily API 并标准化返回结构。"""
        self.assert_supports(capability_id)
        query = (params.get("query") or "").strip()
        if not query:
            raise ProviderInvokeError("query 不能为空")
        if not settings.tavily_api_key:
            raise ProviderInvokeError("缺少 TAVILY_API_KEY")

        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": settings.tavily_search_depth,
            "include_answer": settings.tavily_include_answer,
            "include_raw_content": settings.tavily_include_raw_content,
            "max_results": params.get("max_results") or settings.tavily_max_results,
        }
        data = _post_json(
            url=settings.tavily_api_url,
            payload=payload,
            headers={"Content-Type": "application/json"},
            timeout=settings.tavily_timeout_seconds,
        )
        return self.normalize_response(query, data)


class BaiduWebSearchAdapter(BaseCapabilityAdapter):
    """百度网页检索适配器。"""

    def __init__(self) -> None:
        super().__init__(provider_id="baidu")

    def supported_capabilities(self) -> frozenset[str]:
        """声明支持的能力集合。"""
        return frozenset({"web_search"})

    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        """将百度原始响应转换为统一结构。"""
        return normalize_baidu_response(self.provider_id, query, raw_response).to_payload()

    async def invoke(self, capability_id: str, **params: Any) -> dict[str, Any]:
        """调用千帆 AI Search `POST /v2/ai_search/web_search`（非 chat/completions）。"""
        self.assert_supports(capability_id)
        query = (params.get("query") or "").strip()
        if not query:
            raise ProviderInvokeError("query 不能为空")
        if not settings.baidu_search_api_key:
            raise ProviderInvokeError("缺少 BAIDU_SEARCH_API_KEY")

        data = _qianfan_web_search_request(
            query,
            max_results_param=params.get("max_results"),
            default_max_results=settings.baidu_search_max_results,
            api_key=settings.baidu_search_api_key,
            api_url=settings.baidu_search_api_url,
            search_source=settings.baidu_search_source,
            timeout=settings.baidu_search_timeout_seconds,
        )
        return self.normalize_response(query, data)


class VolcengineWebSearchAdapter(BaseCapabilityAdapter):
    """火山引擎联网检索适配器。"""

    def __init__(self) -> None:
        super().__init__(provider_id="volcengine")

    def supported_capabilities(self) -> frozenset[str]:
        """声明支持的能力集合。"""
        return frozenset({"web_search"})

    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        """将火山原始响应转换为统一结构。"""
        return normalize_volcengine_response(self.provider_id, query, raw_response).to_payload()

    async def invoke(self, capability_id: str, **params: Any) -> dict[str, Any]:
        """字节系 FeedCoop ``POST .../search_api/web_search``（非千帆/Ark 协议）。"""
        self.assert_supports(capability_id)
        query = (params.get("query") or "").strip()
        if not query:
            raise ProviderInvokeError("query 不能为空")
        if not settings.volcengine_search_api_key:
            raise ProviderInvokeError("缺少 VOLCENGINE_SEARCH_API_KEY")

        data = _feedcoop_web_search_request(
            query,
            max_results_param=params.get("max_results"),
            default_max_results=settings.volcengine_search_max_results,
            api_key=settings.volcengine_search_api_key,
            api_url=settings.volcengine_search_api_url,
            timeout=settings.volcengine_search_timeout_seconds,
            search_type=settings.volcengine_search_type,
            need_content=settings.volcengine_search_need_content,
            need_summary=settings.volcengine_search_need_summary,
        )
        err_msg = _feedcoop_error_message(data)
        if err_msg:
            raise ProviderInvokeError(err_msg)
        return self.normalize_response(query, data)
