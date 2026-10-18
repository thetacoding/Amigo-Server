"""Intent route definitions loaded by semantic-router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from semantic_router import Route

_DEFAULT_INTENT_ROUTES_PATH = Path("data/intent_routes.yaml")


def load_intent_routes(file_path: str | Path | None = None) -> list[Route]:
    """Load intent routes from YAML and convert them to semantic-router Route."""
    target = Path(file_path) if file_path is not None else _DEFAULT_INTENT_ROUTES_PATH
    if not target.exists():
        return []

    with target.open("r", encoding="utf-8") as f:
        payload: dict[str, Any] = yaml.safe_load(f) or {}

    raw_routes = payload.get("routes") or []
    routes: list[Route] = []
    for item in raw_routes:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        utterances = item.get("utterances") or []
        if not name or not isinstance(utterances, list) or not utterances:
            continue
        routes.append(
            Route(
                name=name,
                utterances=[str(u) for u in utterances if str(u).strip()],
                description=item.get("description"),
                score_threshold=item.get("score_threshold"),
                metadata=item.get("metadata") or {},
            )
        )
    return routes
