"""Output helpers for eval jobs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def make_output_path(*, output_dir: str, task_name: str) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / f"{task_name}_{ts}.json"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
