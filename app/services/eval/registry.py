"""Registry for scene/task -> evaluator mapping."""

from __future__ import annotations

from app.services.eval.base import BaseEvaluator
from app.services.eval.evaluators.intent_classification import IntentClassificationEvaluator


class EvaluatorRegistry:
    """In-memory evaluator registry."""

    def __init__(self) -> None:
        self._evaluators: dict[tuple[str, str], BaseEvaluator] = {}

    def register(self, evaluator: BaseEvaluator) -> None:
        key = (evaluator.scene, evaluator.task)
        self._evaluators[key] = evaluator

    def get(self, scene: str, task: str) -> BaseEvaluator | None:
        return self._evaluators.get((scene, task))


def build_default_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()
    registry.register(IntentClassificationEvaluator())
    return registry
