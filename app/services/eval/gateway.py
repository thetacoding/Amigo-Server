"""Unified evaluation gateway service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.eval.registry import EvaluatorRegistry, build_default_registry


class EvalGatewayService:
    """Single entry for all evaluation scenes/tasks."""

    def __init__(self, registry: EvaluatorRegistry) -> None:
        self._registry = registry

    async def run(
        self,
        *,
        scene: str,
        task: str,
        inputs: dict[str, Any],
        options: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        evaluator = self._registry.get(scene, task)
        if evaluator is None:
            raise ValueError(f"不支持的评测场景: scene={scene!r}, task={task!r}")
        return await evaluator.evaluate(
            inputs=inputs,
            options=options,
            context=context,
        )


@lru_cache(maxsize=1)
def get_eval_gateway_service() -> EvalGatewayService:
    return EvalGatewayService(registry=build_default_registry())
