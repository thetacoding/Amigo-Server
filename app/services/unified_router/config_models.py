"""路由配置的 Pydantic 模型，便于校验与加载 JSON/YAML。"""

from pydantic import BaseModel, Field


class CapabilityRoutingRule(BaseModel):
    """单个能力的路由策略。"""

    priority: list[str] = Field(
        ...,
        description="供应商 id 优先级列表，靠前的优先尝试",
    )
    fallback: bool = Field(
        default=True,
        description="为 True 时，某供应商失败后继续尝试链路上下一个",
    )


class UnifiedRouterConfig(BaseModel):
    """整套路由配置（可与业务配置、环境变量合并后构造）。"""

    capabilities: dict[str, CapabilityRoutingRule] = Field(
        default_factory=dict,
        description="能力 id -> 路由规则",
    )
