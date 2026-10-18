"""基于 unified_router 的 Web Search 聚合服务。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.config_service import ConfigService
from app.services.unified_router import (
    CapabilityRoutingRule,
    RouteResult,
    UnifiedRouterConfig,
    UnifiedServiceRouter,
)

from .providers import BaiduWebSearchAdapter, TavilyWebSearchAdapter, VolcengineWebSearchAdapter

_KNOWN_PROVIDER_IDS = frozenset({"tavily", "baidu", "volcengine"})
_DEFAULT_PRIORITY: tuple[str, ...] = ("tavily", "baidu", "volcengine")


def _normalize_provider_priority(raw: Any) -> tuple[str, ...]:
    """从配置读取的列表去重、过滤未知 id；空则回退默认顺序。"""
    if not raw or not isinstance(raw, (list, tuple)):
        return _DEFAULT_PRIORITY
    seen: set[str] = set()
    out: list[str] = []
    for p in raw:
        if not isinstance(p, str):
            continue
        pid = p.strip()
        if pid in _KNOWN_PROVIDER_IDS and pid not in seen:
            seen.add(pid)
            out.append(pid)
    return tuple(out) if out else _DEFAULT_PRIORITY


class UnifiedWebSearchService:
    """统一网页检索服务，对外暴露稳定的 blocks/markdown 结构。"""

    def __init__(self, router: UnifiedServiceRouter) -> None:
        self._router = router

    @classmethod
    def build(
        cls,
        *,
        provider_priority: tuple[str, ...] | list[str] | None = None,
        fallback: bool = True,
    ) -> "UnifiedWebSearchService":
        """
        按给定优先级构建路由；缺省为代码内默认顺序。

        线上入口请用 ``get_unified_web_search_service()``（读云端配置）。
        """
        priority = _normalize_provider_priority(provider_priority)
        config = UnifiedRouterConfig(
            capabilities={
                "web_search": CapabilityRoutingRule(
                    priority=list(priority),
                    fallback=fallback,
                )
            }
        )
        router = UnifiedServiceRouter(config)
        router.register_adapter(TavilyWebSearchAdapter())
        router.register_adapter(BaiduWebSearchAdapter())
        router.register_adapter(VolcengineWebSearchAdapter())
        return cls(router)

    @staticmethod
    def _route_result_to_payload(result: RouteResult) -> dict[str, Any]:
        payload = dict(result.data)
        payload["provider"] = result.provider_id
        return payload

    def search(
        self,
        query: str,
        *,
        max_results: int | None = None,
        preferred_provider: str | None = None,
        strict_preferred: bool = False,
    ) -> dict[str, Any]:
        """同步搜索（无已运行中的事件循环时使用）。ASGI/异步上下文须用 asearch。"""
        result = self._router.execute_sync(
            "web_search",
            params={"query": query, "max_results": max_results},
            preferred_provider=preferred_provider,
            strict_preferred=strict_preferred,
        )
        return self._route_result_to_payload(result)

    async def asearch(
        self,
        query: str,
        *,
        max_results: int | None = None,
        preferred_provider: str | None = None,
        strict_preferred: bool = False,
    ) -> dict[str, Any]:
        """异步搜索，在已有事件循环内（如 FastAPI/uvicorn）须使用此入口。"""
        result = await self._router.execute(
            "web_search",
            params={"query": query, "max_results": max_results},
            preferred_provider=preferred_provider,
            strict_preferred=strict_preferred,
        )
        return self._route_result_to_payload(result)

    @staticmethod
    def to_readable_blocks(result: dict[str, Any], content_max_len: int = 280) -> dict[str, Any]:
        """转换为端侧友好的结构化 blocks。"""
        items = []
        for idx, item in enumerate(result.get("results", []), start=1):
            content = (item.get("content") or "").strip()
            snippet = content[:content_max_len] + ("..." if len(content) > content_max_len else "")
            items.append(
                {
                    "index": idx,
                    "title": item.get("title") or "Untitled",
                    "url": item.get("url") or "",
                    "score": item.get("score"),
                    "snippet": snippet,
                }
            )
        return {
            "provider": result.get("provider"),
            "query": result.get("query", ""),
            "answer": result.get("answer") or "",
            "request_id": result.get("request_id"),
            "results": items,
        }

    @classmethod
    def to_markdown(cls, result: dict[str, Any], content_max_len: int = 280) -> str:
        """转换为 Markdown 供 SSE/普通接口直出。"""
        data = cls.to_readable_blocks(result, content_max_len=content_max_len)
        if not data["results"]:
            return "暂未检索到可用来源。"
        lines = ["# Web Search Result", "", "## Sources", ""]
        for item in data["results"]:
            lines.append(f"- [{item['title']}]({item['url']})")
        return "\n".join(lines)


@lru_cache(maxsize=8)
def _cached_unified_web_search_service(
    provider_priority: tuple[str, ...],
    fallback: bool,
) -> UnifiedWebSearchService:
    return UnifiedWebSearchService.build(
        provider_priority=provider_priority,
        fallback=fallback,
    )


def get_unified_web_search_service() -> UnifiedWebSearchService:
    """
    使用 ``data/presets.yaml`` 中 ``app_config.web_search`` 的供应商顺序与 fallback。

    配置键：``provider_priority``（列表）、``fallback``（默认 true）。
    端侧单次覆盖请用 Chat API ``options.web_search_preferred_provider``。
    """
    cfg = ConfigService.get_web_search_config()
    priority = _normalize_provider_priority(cfg.get("provider_priority"))
    fallback = bool(cfg.get("fallback", True))
    return _cached_unified_web_search_service(priority, fallback)
