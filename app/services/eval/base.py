"""Base interfaces for evaluation gateway."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    """Base evaluator contract for a scene/task."""

    scene: str
    task: str

    @abstractmethod
    async def evaluate(
        self,
        *,
        inputs: dict[str, Any],
        options: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute evaluation and return normalized payload."""
