"""Web Search 统一返回模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WebSearchItem(BaseModel):
    """单条检索结果。"""

    title: str = Field(default="Untitled")
    url: str = Field(default="")
    content: str = Field(default="")
    score: float | None = Field(default=None)
    snippet: str | None = Field(default=None)
    raw_content: str | None = Field(default=None)
    website_title: str | None = Field(default=None)
    site: str | None = Field(default=None)
    page_date: str | None = Field(default=None)
    page_type: str | None = Field(default=None)
    images: list[str] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)


class WebSearchResult(BaseModel):
    """统一检索结果结构。"""

    provider: str
    query: str
    answer: str | None = Field(default=None)
    request_id: str | None = Field(default=None)
    results: list[WebSearchItem] = Field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        """导出给 router/service 使用的 dict。"""
        return self.model_dump()
