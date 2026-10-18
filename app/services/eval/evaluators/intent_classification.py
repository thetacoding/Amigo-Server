"""Intent classification evaluator for unified eval gateway."""

from __future__ import annotations

import time
from typing import Any

from app.services.eval.base import BaseEvaluator
from app.services.unified_router.capabilities.intent_classifier import get_intent_router_service


class IntentClassificationEvaluator(BaseEvaluator):
    scene = "nlp"
    task = "intent_classification"

    async def evaluate(
        self,
        *,
        inputs: dict[str, Any],
        options: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        start = time.perf_counter()
        service = get_intent_router_service()
        queries: list[str] = list(inputs.get("queries") or [])
        top_k = options.get("top_k")
        continue_on_error = bool(options.get("continue_on_error", True))

        items: list[dict[str, Any]] = []
        matched_count = 0
        fallback_count = 0
        for idx, query in enumerate(queries):
            try:
                result = service.classify_with_scores(query, top_k=top_k)
                matched_count += 1 if result.matched else 0
                fallback_count += 0 if result.matched else 1
                items.append(
                    {
                        "index": idx,
                        "query": query,
                        "prediction": {
                            "label": result.intent,
                            "score": result.score,
                            "score_type": "aggregated_route_score",
                            "matched": result.matched,
                        },
                        "scores": [s.model_dump() for s in result.scores],
                        "scores_type": "per_label_stats_from_retrieved_utterances",
                        "threshold": result.threshold,
                    }
                )
            except Exception as e:  # noqa: BLE001
                if not continue_on_error:
                    raise
                fallback_count += 1
                items.append(
                    {
                        "index": idx,
                        "query": query,
                        "prediction": {
                            "label": "unknown",
                            "score": None,
                            "matched": False,
                        },
                        "scores": [],
                        "error": str(e),
                    }
                )

        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "scene": self.scene,
            "task": self.task,
            "summary": {
                "total": len(queries),
                "matched": matched_count,
                "fallback": fallback_count,
            },
            "items": items,
            "threshold": {
                "effective": service.score_threshold,
                "source": "intent_router_service",
            },
            "meta": {
                "engine": "semantic-router",
                "encoder": "fastembed",
                "model": service.model_name,
                "latency_ms": latency_ms,
                "request_context": {
                    "session_id": context.get("session_id"),
                    "interaction_id": context.get("interaction_id"),
                },
            },
        }
