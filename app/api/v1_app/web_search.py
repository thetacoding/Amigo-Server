from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.base import ResponseModel
from app.services.web_search.tavily_search import TavilyWebSearchService

router = APIRouter()


class WebSearchRequest(BaseModel):
    query: str = Field(..., description="检索关键词")
    format: Literal["markdown", "blocks", "both"] = Field(
        default="both", description="返回格式：markdown / blocks / both"
    )
    max_results: Optional[int] = Field(default=None, description="可选，临时覆盖返回条数")
    content_max_len: int = Field(default=280, description="每条摘要最大长度")


@router.post("/tavily/readable")
async def tavily_readable_search(req: WebSearchRequest):
    try:
        raw_result = TavilyWebSearchService.search(req.query)
        if req.max_results is not None and req.max_results >= 0:
            raw_result["results"] = (raw_result.get("results") or [])[: req.max_results]

        blocks = TavilyWebSearchService.to_readable_blocks(raw_result, content_max_len=req.content_max_len)
        markdown = TavilyWebSearchService.to_markdown(raw_result, content_max_len=req.content_max_len)

        if req.format == "markdown":
            payload = {"query": req.query, "markdown": markdown}
        elif req.format == "blocks":
            payload = blocks
        else:
            payload = {"blocks": blocks, "markdown": markdown}

        return ResponseModel(data=payload)
    except Exception as e:
        return ResponseModel(code=500, msg=str(e))
