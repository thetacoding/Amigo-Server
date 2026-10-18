"""额度/限流状态抽象：默认内存实现，后续可替换为 Redis 等。"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class QuotaStore(Protocol):
    """额度状态存储协议。"""

    def is_exhausted(self, provider_id: str, capability_id: str) -> bool:
        """检查指定供应商能力的额度是否耗尽。"""
        pass

    def mark_exhausted(
        self,
        provider_id: str,
        capability_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        """标记指定供应商能力的额度耗尽，可设置过期时间。"""
        pass

    def clear(self, provider_id: str, capability_id: str) -> None:
        """清除指定供应商能力的额度耗尽标记。"""
        pass


class InMemoryQuotaStore:
    """进程内额度状态；重启后清空。生产可换 Redis 实现同一协议。"""

    def __init__(self) -> None:
        self._until: dict[tuple[str, str], float] = {}

    def is_exhausted(self, provider_id: str, capability_id: str) -> bool:
        """检查指定供应商能力的额度是否耗尽。"""
        key = (provider_id, capability_id)
        until = self._until.get(key)
        if until is None:
            return False
        if time.monotonic() < until:
            return True
        del self._until[key]
        return False

    def mark_exhausted(
        self,
        provider_id: str,
        capability_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        """标记指定供应商能力的额度耗尽，可设置过期时间。"""
        key = (provider_id, capability_id)
        ttl = ttl_seconds if ttl_seconds is not None else 3600
        self._until[key] = time.monotonic() + max(1, ttl)

    def clear(self, provider_id: str, capability_id: str) -> None:
        """清除指定供应商能力的额度耗尽标记。"""
        self._until.pop((provider_id, capability_id), None)
