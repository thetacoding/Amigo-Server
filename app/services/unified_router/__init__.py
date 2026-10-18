"""
通用能力路由（Unified Service Router）：多品类 API、多厂商优先级与指定调用。

不修改既有 LLM / 搜索等模块；新业务可逐步将适配器注册到此路由器上。
"""

from app.services.unified_router.adapter import BaseCapabilityAdapter
from app.services.unified_router.config_models import CapabilityRoutingRule, UnifiedRouterConfig
from app.services.unified_router.exceptions import (
    AllProvidersExhaustedError,
    CapabilityNotConfiguredError,
    CapabilityNotSupportedError,
    ProviderInvokeError,
    ProviderNotRegisteredError,
    QuotaExhaustedError,
    UnifiedRouterError,
)
from app.services.unified_router.quota import InMemoryQuotaStore, QuotaStore
from app.services.unified_router.router import RouteAttempt, RouteResult, UnifiedServiceRouter

__all__ = [
    "AllProvidersExhaustedError",
    "BaseCapabilityAdapter",
    "CapabilityNotConfiguredError",
    "CapabilityNotSupportedError",
    "CapabilityRoutingRule",
    "InMemoryQuotaStore",
    "ProviderInvokeError",
    "ProviderNotRegisteredError",
    "QuotaExhaustedError",
    "QuotaStore",
    "RouteAttempt",
    "RouteResult",
    "UnifiedRouterConfig",
    "UnifiedRouterError",
    "UnifiedServiceRouter",
]
