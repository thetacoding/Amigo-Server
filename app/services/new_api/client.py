from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def normalized_newapi_v1_base() -> str:
    """OpenAI 兼容根路径，例如 `http://host:3000/v1`（无尾部斜杠）。"""
    return (settings.newapi_base_url or "").rstrip("/")


class NewApiClient:
    """
    New API 网关异步 HTTP 客户端。

    用于 OpenAI 兼容协议之外的直连 REST（如 GET /v1/models）。
    Chat completions 由 LangChain ChatOpenAI 发起，与本类共享 `settings` 中的
    `newapi_base_url` / `newapi_api_key`。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base = (base_url or normalized_newapi_v1_base()).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.newapi_api_key
        self._timeout = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    async def list_models(self) -> dict[str, Any]:
        """GET /v1/models，返回原始 JSON（结构随网关版本可能略有差异）。"""
        url = f"{self._base}/models"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()


def new_api_client_from_settings() -> NewApiClient:
    return NewApiClient()
