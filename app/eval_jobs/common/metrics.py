"""Lightweight classification metrics."""

from __future__ import annotations

from collections import defaultdict


def classification_metrics(gold: list[str], pred: list[str]) -> dict:
    total = len(gold)
    if total == 0:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "total": 0,
        }

    labels = sorted(set(gold) | set(pred))
    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    accuracy = correct / total

    per_label = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for label in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
        support = sum(1 for g in gold if g == label)

        precision = tp / (tp + fp) if tp + fp > 0 else 0.0
        recall = tp / (tp + fn) if tp + fn > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        per_label[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": support,
        }
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    return {
        "accuracy": round(accuracy, 6),
        "macro_precision": round(sum(precisions) / len(precisions), 6),
        "macro_recall": round(sum(recalls) / len(recalls), 6),
        "macro_f1": round(sum(f1s) / len(f1s), 6),
        "total": total,
        "per_label": per_label,
    }


def confusion_top(gold: list[str], pred: list[str], top_n: int = 20) -> list[dict]:
    bucket = defaultdict(int)
    for g, p in zip(gold, pred):
        if g == p:
            continue
        bucket[(g, p)] += 1
    pairs = sorted(bucket.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{"gold": g, "pred": p, "count": c} for (g, p), c in pairs]
