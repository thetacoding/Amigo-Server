"""不同厂商响应体 -> WebSearchResult 的标准化转换。"""

from __future__ import annotations

from typing import Any

from .models import WebSearchItem, WebSearchResult


def _pick_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("results") or data.get("data") or data.get("items") or []
    if isinstance(rows, list):
        return [x for x in rows if isinstance(x, dict)]
    return []


def normalize_tavily_response(provider_id: str, query: str, data: dict[str, Any]) -> WebSearchResult:
    """Tavily 响应标准化。"""
    rows = data.get("results")
    items: list[WebSearchItem] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            images = row.get("images")
            videos = row.get("videos")
            items.append(
                WebSearchItem(
                    title=row.get("title") or "Untitled",
                    url=row.get("url") or "",
                    content=row.get("content") or row.get("snippet") or "",
                    score=row.get("score"),
                    snippet=row.get("snippet"),
                    raw_content=row.get("raw_content"),
                    website_title=row.get("title"),
                    site=row.get("site"),
                    page_date=row.get("published_date") or row.get("page_date"),
                    page_type=row.get("type"),
                    images=[x for x in images if isinstance(x, str)] if isinstance(images, list) else [],
                    videos=[x for x in videos if isinstance(x, str)] if isinstance(videos, list) else [],
                )
            )
    return WebSearchResult(
        provider=provider_id,
        query=data.get("query", query),
        answer=data.get("answer"),
        request_id=data.get("request_id"),
        results=items,
    )


def _pick_qianfan_web_references(data: dict[str, Any]) -> list[dict[str, Any]]:
    """千帆 /v2/ai_search/web_search 成功体为 references[]（含 title、url、content、snippet 等）。"""
    refs = data.get("references")
    if isinstance(refs, list) and refs:
        return refs
    return _pick_items(data)


def _normalize_qianfan_web_search_result(
    provider_id: str, query: str, data: dict[str, Any]
) -> WebSearchResult:
    """千帆 /v2/ai_search/web_search 的 references 等字段解析。"""
    refs = _pick_qianfan_web_references(data)
    items: list[WebSearchItem] = []
    for row in refs:
        if not isinstance(row, dict):
            continue
        # 百度 references 里 image/video 往往是单个字符串；统一转成列表字段。
        image = row.get("image")
        video = row.get("video")
        images = row.get("images")
        videos = row.get("videos")
        normalized_images: list[str] = []
        normalized_videos: list[str] = []
        if isinstance(image, str) and image:
            normalized_images.append(image)
        if isinstance(video, str) and video:
            normalized_videos.append(video)
        if isinstance(images, list):
            normalized_images.extend([x for x in images if isinstance(x, str)])
        if isinstance(videos, list):
            normalized_videos.extend([x for x in videos if isinstance(x, str)])
        items.append(
            WebSearchItem(
                title=row.get("title") or "Untitled",
                url=row.get("url") or row.get("link") or "",
                content=row.get("content") or row.get("snippet") or "",
                score=row.get("score"),
                snippet=row.get("snippet"),
                raw_content=row.get("raw_content"),
                website_title=row.get("title"),
                site=row.get("site") or row.get("source"),
                page_date=row.get("date") or row.get("publish_time"),
                page_type=row.get("type"),
                images=normalized_images,
                videos=normalized_videos,
            )
        )
    return WebSearchResult(
        provider=provider_id,
        query=data.get("query", query),
        answer=data.get("answer") or data.get("summary"),
        request_id=data.get("request_id") or data.get("requestId") or data.get("id"),
        results=items,
    )


def normalize_baidu_response(provider_id: str, query: str, data: dict[str, Any]) -> WebSearchResult:
    """百度千帆 web_search 响应。"""
    return _normalize_qianfan_web_search_result(provider_id, query, data)


def normalize_volcengine_response(provider_id: str, query: str, data: dict[str, Any]) -> WebSearchResult:
    """火山（字节 FeedCoop）web_search：Result.WebResults、ResponseMetadata.RequestId。"""
    result_block = data.get("Result")
    if not isinstance(result_block, dict):
        result_block = {}
    web = result_block.get("WebResults")
    rows: list[dict[str, Any]] = web if isinstance(web, list) else []
    if not rows:
        # 兼容小写结构
        fallback_rows = data.get("results") or data.get("data") or data.get("items") or []
        if isinstance(fallback_rows, list):
            rows = [x for x in fallback_rows if isinstance(x, dict)]
    request_id: str | None = None
    meta = data.get("ResponseMetadata")
    if isinstance(meta, dict):
        request_id = meta.get("RequestId") or meta.get("RequestID")
    answer = result_block.get("Summary") or result_block.get("summary")
    items: list[WebSearchItem] = []
    for row in rows:
        images = row.get("Images") or row.get("images")
        videos = row.get("Videos") or row.get("videos")
        title = row.get("Title") or row.get("title") or "Untitled"
        url = row.get("Url") or row.get("url") or row.get("Link") or ""
        snippet = row.get("Snippet") or row.get("snippet")
        content = row.get("Content") or row.get("content") or snippet or ""
        items.append(
            WebSearchItem(
                title=title,
                url=url,
                content=content,
                score=row.get("Score") or row.get("score"),
                snippet=snippet,
                raw_content=row.get("RawContent") or row.get("raw_content"),
                website_title=title,
                site=row.get("Site") or row.get("site") or row.get("Source") or row.get("source"),
                page_date=row.get("PublishTime") or row.get("publish_time") or row.get("Date") or row.get("date"),
                page_type=row.get("Type") or row.get("type"),
                images=[x for x in images if isinstance(x, str)] if isinstance(images, list) else [],
                videos=[x for x in videos if isinstance(x, str)] if isinstance(videos, list) else [],
            )
        )
    return WebSearchResult(
        provider=provider_id,
        query=query,
        answer=answer,
        request_id=request_id or data.get("request_id"),
        results=items,
    )
