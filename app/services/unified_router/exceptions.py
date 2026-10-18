"""统一能力路由相关异常。"""


class UnifiedRouterError(Exception):
    """路由层基础异常。"""


class ProviderNotRegisteredError(UnifiedRouterError):
    """配置或调用中引用了未注册的供应商适配器。"""


class CapabilityNotConfiguredError(UnifiedRouterError):
    """当前路由配置未声明该能力的路由规则。"""


class CapabilityNotSupportedError(UnifiedRouterError):
    """适配器声明不支持该能力。"""


class QuotaExhaustedError(UnifiedRouterError):
    """供应商在该能力上额度耗尽或返回可识别的限流错误。"""


class AllProvidersExhaustedError(UnifiedRouterError):
    """按策略尝试后仍无可用供应商。"""


class ProviderInvokeError(UnifiedRouterError):
    """单次供应商调用失败（非额度类或调用方选择不重试）。"""
