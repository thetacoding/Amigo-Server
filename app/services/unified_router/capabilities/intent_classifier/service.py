"""Semantic-router based intent classification service (singleton entry)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from semantic_router import SemanticRouter
from semantic_router.encoders.fastembed import FastEmbedEncoder

from .config import get_intent_classifier_config, load_score_threshold_from_routes_file
from .routes import load_intent_routes
from .schemas import IntentClassifyDetailedResult, IntentClassifyResult, IntentScoreItem


class IntentRouterService:
    """Intent router capability built on semantic-router + fastembed."""

    def __init__(
        self,
        router: SemanticRouter,
        *,
        model_name: str,
        score_threshold: float,
        fallback_intent: str = "unknown",
    ) -> None:
        self._router = router
        self._model_name = model_name
        self._score_threshold = score_threshold
        self._fallback_intent = fallback_intent

    @classmethod
    def build(
        cls,
        *,
        model_name: str,
        score_threshold: float,
        fallback_intent: str,
        intent_routes_path: str,
    ) -> "IntentRouterService":
        routes = load_intent_routes(intent_routes_path)
        encoder = FastEmbedEncoder(name=model_name, score_threshold=score_threshold)
        router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")
        return cls(
            router,
            model_name=model_name,
            score_threshold=score_threshold,
            fallback_intent=fallback_intent,
        )

    def classify(self, text: str) -> IntentClassifyResult:
        """Classify a single text into intent."""
        query = (text or "").strip()
        if not query:
            return IntentClassifyResult(
                text=text,
                intent=self._fallback_intent,
                score=None,
                matched=False,
                fallback_intent=self._fallback_intent,
            )

        route_choice = self._router(query)
        return self._to_result(text=query, route_choice=route_choice)

    def classify_with_scores(
        self,
        text: str,
        *,
        top_k: int | None = None,
    ) -> IntentClassifyDetailedResult:
        """Classify and return per-intent scores with threshold."""
        query = (text or "").strip()
        if not query:
            return IntentClassifyDetailedResult(
                text=text,
                intent=self._fallback_intent,
                score=None,
                matched=False,
                fallback_intent=self._fallback_intent,
                scores=[],
                threshold=self._score_threshold,
            )

        route_choice = self._router(query)
        scores = self._collect_scores(query, top_k=top_k)
        base = self._to_result(text=query, route_choice=route_choice)
        return IntentClassifyDetailedResult(
            **base.model_dump(),
            scores=scores,
            threshold=self._score_threshold,
        )

    async def aclassify(self, text: str) -> IntentClassifyResult:
        """Async classify for FastAPI async contexts."""
        query = (text or "").strip()
        if not query:
            return IntentClassifyResult(
                text=text,
                intent=self._fallback_intent,
                score=None,
                matched=False,
                fallback_intent=self._fallback_intent,
            )

        route_choice = await self._router.acall(query)
        return self._to_result(text=query, route_choice=route_choice)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    def _to_result(self, *, text: str, route_choice: Any) -> IntentClassifyResult:
        name = getattr(route_choice, "name", None)
        score = getattr(route_choice, "similarity_score", None)
        matched = bool(name)
        return IntentClassifyResult(
            text=text,
            intent=name or self._fallback_intent,
            score=score,
            matched=matched,
            fallback_intent=self._fallback_intent,
        )

    def _collect_scores(self, query: str, *, top_k: int | None = None) -> list[IntentScoreItem]:
        """
        Collect per-intent scores from semantic-router index retrieval.
        Returns both max and mean score for each intent label.
        """
        vector = self._router._encode(text=[query], input_type="queries")  # noqa: SLF001
        utterances = self._router.index.get_utterances(include_metadata=False)
        total = len(utterances or [])
        if total == 0:
            return []

        query_k = total if top_k is None else max(1, min(top_k, total))
        scores, routes = self._router.index.query(  # route ids with potentially duplicated labels
            vector=vector[0],
            top_k=query_k,
            route_filter=None,
        )

        merged: dict[str, list[float]] = {}
        for route_name, score in zip(routes, scores):
            value = float(score)
            if route_name not in merged:
                merged[route_name] = []
            merged[route_name].append(value)

        items = []
        for label, values in merged.items():
            score_max = max(values)
            score_mean = sum(values) / len(values)
            items.append(
                IntentScoreItem(
                    label=label,
                    score_max=score_max,
                    score_mean=score_mean,
                    utterance_hits=len(values),
                )
            )
        return sorted(items, key=lambda x: x.score_max, reverse=True)


@lru_cache(maxsize=1)
def get_intent_router_service() -> IntentRouterService:
    """
    Singleton-like service entry for app lifecycle reuse.
    Config source:
    - `data/presets.yaml` -> `app_config.intent_router`
    - optional `data/intent_routes.yaml` -> `defaults.score_threshold`
    """
    cfg = get_intent_classifier_config()
    routes_threshold = load_score_threshold_from_routes_file(cfg["intent_routes_path"])
    threshold = float(routes_threshold) if routes_threshold is not None else float(cfg["score_threshold"])

    return IntentRouterService.build(
        model_name=str(cfg["model_name"]),
        score_threshold=threshold,
        fallback_intent=str(cfg["fallback_intent"]),
        intent_routes_path=str(cfg["intent_routes_path"]),
    )
