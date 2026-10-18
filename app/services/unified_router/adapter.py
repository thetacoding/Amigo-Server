"""供应商适配器基类：同一类可承载多个能力及同端点多参数模式。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .exceptions import CapabilityNotSupportedError


class BaseCapabilityAdapter(ABC):
    """
    厂商侧统一入口：在 _invoke 内按 capability_id 分支。
    同一 HTTP 接口、不同参数（如网页 / 视频）放在同一适配器内处理即可。
    """

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    @abstractmethod
    def supported_capabilities(self) -> frozenset[str]:
        """声明本适配器实现的能力 id 集合。"""

    def assert_supports(self, capability_id: str) -> None:
        """断言本适配器支持指定能力。"""
        if capability_id not in self.supported_capabilities():
            raise CapabilityNotSupportedError(
                f"供应商 {self.provider_id!r} 不支持能力 {capability_id!r}"
            )

    @abstractmethod
    async def invoke(self, capability_id: str, **params: Any) -> Any:
        """
        执行调用。params 为统一业务参数；厂商差异在子类内归一化。
        需要同步 IO 时可在实现中使用 asyncio.to_thread。
        """

    @abstractmethod
    def normalize_response(self, query: str, raw_response: dict[str, Any]) -> dict[str, Any]:
        """将厂商原始响应转换为统一结构。"""
