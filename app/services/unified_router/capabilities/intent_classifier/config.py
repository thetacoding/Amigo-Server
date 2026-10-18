"""Intent classifier runtime config helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.services.config_service import ConfigService

_DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_DEFAULT_SCORE_THRESHOLD = 0.5
_DEFAULT_FALLBACK_INTENT = "unknown"
_DEFAULT_INTENT_ROUTES_PATH = "data/intent_routes.yaml"


def get_intent_classifier_config() -> dict[str, Any]:
    """Read app_config.intent_router with defaults."""
    app = ConfigService.get_app_config() or {}
    cfg = dict(app.get("intent_router") or {})
    cfg.setdefault("model_name", _DEFAULT_MODEL_NAME)
    cfg.setdefault("score_threshold", _DEFAULT_SCORE_THRESHOLD)
    cfg.setdefault("fallback_intent", _DEFAULT_FALLBACK_INTENT)
    cfg.setdefault("intent_routes_path", _DEFAULT_INTENT_ROUTES_PATH)
    return cfg


def load_score_threshold_from_routes_file(intent_routes_path: str | Path) -> float | None:
    """
    Optional global threshold in routes YAML.
    Uses key: `defaults.score_threshold`.
    """
    target = Path(intent_routes_path)
    if not target.exists():
        return None

    with target.open("r", encoding="utf-8") as f:
        payload: dict[str, Any] = yaml.safe_load(f) or {}
    defaults = payload.get("defaults") or {}
    value = defaults.get("score_threshold")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
