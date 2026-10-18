"""统一能力路由：优先级链、指定供应商、strict 与 fallback 语义。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from loguru import logger

from .adapter import BaseCapabilityAdapter
from .config_models import UnifiedRouterConfig, CapabilityRoutingRule
from .exceptions import (
    AllProvidersExhaustedError,
    CapabilityNotConfiguredError,
    CapabilityNotSupportedError,
    ProviderNotRegisteredError,
    QuotaExhaustedError,
)
from .quota import InMemoryQuotaStore, QuotaStore


@dataclass
class RouteAttempt:
    """单次路由尝试的元信息，便于日志与上层展示。"""

    provider_id: str
    capability_id: str
    ok: bool
    error: str | None = None


@dataclass
class RouteResult:
    """路由执行结果。"""

    data: Any
    provider_id: str
    capability_id: str
    attempts: list[RouteAttempt]


class UnifiedServiceRouter:
    """
    按能力 id 在多个供应商之间调度；支持指定首选供应商与 strict 模式。
    """

    def __init__(
        self,
        config: UnifiedRouterConfig,
        *,
        quota_store: QuotaStore | None = None,
        on_quota_exhausted: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self._config = config
        self._adapters: dict[str, BaseCapabilityAdapter] = {}
        self._quota: QuotaStore = quota_store or InMemoryQuotaStore()
        self._on_quota_exhausted = on_quota_exhausted

    def register_adapter(self, adapter: BaseCapabilityAdapter) -> None:
        """注册单个供应商适配器，provider_id 必须全局唯一。"""
        pid = adapter.provider_id
        if pid in self._adapters:
            raise ValueError(f"供应商适配器已注册: {pid!r}")
        self._adapters[pid] = adapter

    def _rule(self, capability_id: str) -> CapabilityRoutingRule:
        rule = self._config.capabilities.get(capability_id)
        if not rule:
            raise CapabilityNotConfiguredError(f"未配置能力路由: {capability_id!r}")
        return rule

    @staticmethod
    def _build_chain(
        rule: CapabilityRoutingRule,
        *,
        preferred_provider: str | None,
        strict_preferred: bool,
    ) -> list[str]:
        base = list(rule.priority)
        if not preferred_provider:
            return base
        if strict_preferred:
            return [preferred_provider]
        rest = [p for p in base if p != preferred_provider]
        return [preferred_provider] + rest

    async def execute(
        self,
        capability_id: str,
        *,
        params: dict[str, Any] | None = None,
        preferred_provider: str | None = None,
        strict_preferred: bool = False,
    ) -> RouteResult:
        """
        :param capability_id: 能力 id，如 web_search、image_search
        :param params: 传入适配器 invoke 的关键字参数
        :param preferred_provider: 指定优先使用的供应商 id；非 strict 时仍会回落到配置中的其他供应商
        :param strict_preferred: 为 True 时仅调用 preferred_provider，失败即抛出（需同时传入 preferred_provider）
        """
        params = dict(params or {})
        rule = self._rule(capability_id)
        chain = self._build_chain(
            rule,
            preferred_provider=preferred_provider,
            strict_preferred=strict_preferred,
        )
        if strict_preferred and not preferred_provider:
            raise ValueError("strict_preferred=True 时必须提供 preferred_provider")

        attempts: list[RouteAttempt] = []
        last_exc: Exception | None = None

        for provider_id in chain:
            adapter = self._adapters.get(provider_id)
            if adapter is None:
                msg = f"未注册供应商: {provider_id!r}"
                attempts.append(RouteAttempt(provider_id, capability_id, False, msg))
                if not rule.fallback:
                    raise ProviderNotRegisteredError(msg)
                continue

            if capability_id not in adapter.supported_capabilities():
                msg = f"{provider_id!r} 未实现能力 {capability_id!r}"
                attempts.append(RouteAttempt(provider_id, capability_id, False, msg))
                if not rule.fallback:
                    raise CapabilityNotSupportedError(msg)
                continue

            if self._quota.is_exhausted(provider_id, capability_id):
                msg = "额度或限流状态标记为不可用"
                attempts.append(RouteAttempt(provider_id, capability_id, False, msg))
                if not rule.fallback:
                    raise QuotaExhaustedError(msg)
                continue

            try:
                logger.debug(
                    "unified_router invoke capability={} provider={}",
                    capability_id,
                    provider_id,
                )
                data = await adapter.invoke(capability_id, **params)
                attempts.append(RouteAttempt(provider_id, capability_id, True, None))
                return RouteResult(
                    data=data,
                    provider_id=provider_id,
                    capability_id=capability_id,
                    attempts=attempts,
                )
            except QuotaExhaustedError as e:
                last_exc = e
                attempts.append(
                    RouteAttempt(provider_id, capability_id, False, str(e)),
                )
                self._quota.mark_exhausted(provider_id, capability_id)
                if self._on_quota_exhausted is not None:
                    await self._on_quota_exhausted(provider_id, capability_id)
                if not rule.fallback:
                    raise
            except Exception as e:  # noqa: BLE001 — 路由层需聚合各供应商错误
                last_exc = e
                attempts.append(
                    RouteAttempt(provider_id, capability_id, False, str(e)),
                )
                logger.warning(
                    "unified_router capability={} provider={} failed: {}",
                    capability_id,
                    provider_id,
                    e,
                )
                if not rule.fallback:
                    raise

        detail = str(last_exc) if last_exc else "无可用供应商"
        raise AllProvidersExhaustedError(
            f"能力 {capability_id!r} 已全部尝试失败: {detail}",
        ) from last_exc

    def execute_sync(
        self,
        capability_id: str,
        *,
        params: dict[str, Any] | None = None,
        preferred_provider: str | None = None,
        strict_preferred: bool = False,
    ) -> RouteResult:
        """在无非运行中事件循环时使用的同步封装。"""

        return asyncio.run(
            self.execute(
                capability_id,
                params=params,
                preferred_provider=preferred_provider,
                strict_preferred=strict_preferred,
            ),
        )
