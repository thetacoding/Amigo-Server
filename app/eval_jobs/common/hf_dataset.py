"""Helpers for loading and previewing HuggingFace datasets."""

from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset


def load_hf_split(
    *,
    dataset_name: str,
    split: str,
    config_name: str | None = None,
    limit: int | None = None,
) -> Dataset:
    ds = load_dataset(dataset_name, config_name, split=split)
    if limit is not None and limit > 0:
        ds = ds.select(range(min(limit, len(ds))))
    return ds


def preview_hf_split(
    *,
    dataset_name: str,
    split: str,
    config_name: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    ds = load_hf_split(
        dataset_name=dataset_name,
        config_name=config_name,
        split=split,
        limit=limit,
    )
    sample_count = len(ds)
    rows = [dict(row) for row in ds]
    return {
        "dataset_name": dataset_name,
        "config_name": config_name,
        "split": split,
        "columns": list(ds.column_names),
        "features": {k: str(v) for k, v in ds.features.items()},
        "sample_count": sample_count,
        "rows": rows,
    }
