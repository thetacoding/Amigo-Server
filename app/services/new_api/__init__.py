"""
New API 网关集成层。

与 `app/services/ai/llm` 中的 factory/provider 解耦：
- 本包：面向网关的 HTTP 能力（如列举模型），后续可继续扩展其它 REST 接口。
- LLM 对话：仍通过 `LLMFactory` 选择 `provider=newapi`，内部用 LangChain `ChatOpenAI`
  指向同一套 base_url / api_key（见 `client.normalized_newapi_v1_base`）。
"""

from app.services.new_api.client import (
    NewApiClient,
    new_api_client_from_settings,
    normalized_newapi_v1_base,
)

__all__ = [
    "NewApiClient",
    "new_api_client_from_settings",
    "normalized_newapi_v1_base",
]
