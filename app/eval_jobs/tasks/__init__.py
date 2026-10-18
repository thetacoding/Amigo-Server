"""Eval task registry."""

from __future__ import annotations

TASK_REGISTRY = {
    "intent_query": {
        "task_name": "intent_query",
        "default_dataset": "SetFit/amazon_massive_intent_zh-CN",
        "default_split": "test",
        "module_path": "app.eval_jobs.tasks.intent_query_eval",
        "preview_fn_name": "preview_task",
        "run_fn_name": "run_task",
    }
}
