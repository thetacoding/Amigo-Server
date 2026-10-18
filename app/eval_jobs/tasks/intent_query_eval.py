"""Batch eval task: query intent classification."""

from __future__ import annotations

from typing import Any

from datasets import ClassLabel

from app.eval_jobs.common.hf_dataset import load_hf_split, preview_hf_split
from app.eval_jobs.common.metrics import classification_metrics, confusion_top
from app.services.unified_router.capabilities.intent_classifier import get_intent_router_service

TASK_NAME = "intent_query"
DEFAULT_DATASET_NAME = "SetFit/amazon_massive_intent_zh-CN"
DEFAULT_SPLIT = "test"


def _infer_text_column(columns: list[str]) -> str:
    for name in ("query", "text", "utt", "utterance"):
        if name in columns:
            return name
    return columns[0]


def _infer_label_column(columns: list[str]) -> str:
    for name in ("label_text", "intent", "label"):
        if name in columns:
            return name
    if len(columns) >= 2:
        return columns[1]
    return columns[0]


def _label_to_text(raw: Any, *, ds, label_column: str) -> str:
    feature = ds.features.get(label_column)
    if isinstance(feature, ClassLabel) and isinstance(raw, int):
        return str(feature.names[raw])
    return str(raw)


def preview_task(
    *,
    dataset_name: str,
    config_name: str | None,
    split: str,
    limit: int,
) -> dict[str, Any]:
    return preview_hf_split(
        dataset_name=dataset_name,
        config_name=config_name,
        split=split,
        limit=limit,
    )


def run_task(
    *,
    dataset_name: str,
    config_name: str | None,
    split: str,
    limit: int | None,
    top_k: int | None,
) -> dict[str, Any]:
    ds = load_hf_split(
        dataset_name=dataset_name,
        config_name=config_name,
        split=split,
        limit=limit,
    )
    service = get_intent_router_service()

    text_col = _infer_text_column(list(ds.column_names))
    label_col = _infer_label_column(list(ds.column_names))

    gold: list[str] = []
    pred: list[str] = []
    rows: list[dict[str, Any]] = []
    skipped = 0
    for i, row in enumerate(ds):
        query = str(row.get(text_col, "")).strip()
        raw_label = row.get(label_col)
        if not query or raw_label is None:
            skipped += 1
            continue

        gold_label = _label_to_text(raw_label, ds=ds, label_column=label_col)
        result = service.classify_with_scores(query, top_k=top_k)
        pred_label = result.intent
        gold.append(gold_label)
        pred.append(pred_label)
        rows.append(
            {
                "index": i,
                "query": query,
                "gold_label": gold_label,
                "pred_label": pred_label,
                "matched": result.matched,
                "prediction_score": result.score,
                "scores": [x.model_dump() for x in result.scores],
            }
        )

    metrics = classification_metrics(gold, pred)
    badcases = [r for r in rows if r["gold_label"] != r["pred_label"]]
    return {
        "task_name": TASK_NAME,
        "dataset_name": dataset_name,
        "config_name": config_name,
        "split": split,
        "limit": limit,
        "columns": {"text": text_col, "label": label_col},
        "service": {
            "model_name": service.model_name,
            "threshold": service.score_threshold,
        },
        "summary": {
            "rows_total": len(ds),
            "rows_used": len(rows),
            "rows_skipped": skipped,
            **{k: v for k, v in metrics.items() if k != "per_label"},
        },
        "metrics": {
            "overall": {k: v for k, v in metrics.items() if k != "per_label"},
            "per_label": metrics["per_label"],
            "top_confusion": confusion_top(gold, pred, top_n=20),
        },
        "badcases_top20": badcases[:20],
        "rows": rows,
    }
