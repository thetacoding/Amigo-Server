import json
from typing import Any, Dict, Optional
from urllib import error, request

from app.core.config import settings


class TavilyWebSearchService:
    """调用 Tavily Search API 的简单服务封装。"""

    @classmethod
    def search(cls, query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        传入检索关键词，返回 Tavily 检索结果。

        参数:
            query: 检索关键词
            api_key: Tavily API Key，不传时使用配置中的 TAVILY_API_KEY
        """
        if not query or not query.strip():
            raise ValueError("query 不能为空")

        resolved_api_key = api_key or settings.tavily_api_key
        if not resolved_api_key:
            raise ValueError("缺少 Tavily API Key，请在 .env 中设置 TAVILY_API_KEY")

        payload = {
            "api_key": resolved_api_key,
            "query": query.strip(),
            "search_depth": settings.tavily_search_depth,
            "include_answer": settings.tavily_include_answer,
            "include_raw_content": settings.tavily_include_raw_content,
            "max_results": settings.tavily_max_results,
        }
        body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url=settings.tavily_api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=settings.tavily_timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Tavily 请求失败: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Tavily 网络请求异常: {exc.reason}") from exc

    @staticmethod
    def to_readable_blocks(result: Dict[str, Any], content_max_len: int = 280) -> Dict[str, Any]:
        """
        将 Tavily 原始结果转换为便于端侧渲染的结构化内容。
        """
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
            "query": result.get("query", ""),
            "answer": result.get("answer") or "",
            "request_id": result.get("request_id"),
            "response_time": result.get("response_time"),
            "results": items,
        }

    @classmethod
    def to_markdown(cls, result: Dict[str, Any], content_max_len: int = 280) -> str:
        """
        将 Tavily 原始结果转换为可直接展示的 Markdown 文本。
        """
        data = cls.to_readable_blocks(result, content_max_len=content_max_len)

        if not data["results"]:
            return "暂未检索到可用来源。"

        lines = []
        for item in data["results"]:
            lines.append(f"[{item['title']}]({item['url']})")
            lines.append("")

        # 去掉最后一次循环追加的空行，避免文末多余留白。
        if lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)
