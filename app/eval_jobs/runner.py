"""CLI runner for batch evaluation tasks."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
from pathlib import Path

from app.eval_jobs.common.io import make_output_path, write_json
from app.eval_jobs.tasks import TASK_REGISTRY


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch evaluation runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List available eval tasks")

    preview = sub.add_parser("preview", help="Preview dataset schema and examples")
    preview.add_argument("--task", required=True)
    preview.add_argument("--dataset", default="")
    preview.add_argument("--config", default="")
    preview.add_argument("--split", default="")
    preview.add_argument("--limit", type=int, default=5)

    run = sub.add_parser("run", help="Run one eval task")
    run.add_argument("--task", required=True)
    run.add_argument("--dataset", default="")
    run.add_argument("--config", default="")
    run.add_argument("--split", default="")
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--top-k", type=int, default=0)
    run.add_argument("--output-dir", default="outputs/eval")

    run_all = sub.add_parser("run-all", help="Run all eval tasks")
    run_all.add_argument("--output-dir", default="outputs/eval")
    run_all.add_argument("--limit", type=int, default=0)
    run_all.add_argument("--top-k", type=int, default=0)

    clean = sub.add_parser("clean-output", help="Remove all eval outputs")
    clean.add_argument("--output-dir", default="outputs/eval")

    return parser


def _resolve_task_functions(item: dict) -> tuple:
    module = importlib.import_module(item["module_path"])
    preview_fn = getattr(module, item["preview_fn_name"])
    run_fn = getattr(module, item["run_fn_name"])
    return preview_fn, run_fn


def _task_params(task_name: str, dataset: str, config: str, split: str) -> tuple[dict, dict]:
    item = TASK_REGISTRY[task_name]
    params = {
        "dataset_name": dataset or item["default_dataset"],
        "config_name": config or None,
        "split": split or item.get("default_split", "test"),
    }
    return item, params


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.cmd == "list":
        payload = {
            "tasks": [
                {
                    "task_name": name,
                    "default_dataset": item["default_dataset"],
                    "default_split": item.get("default_split", "test"),
                }
                for name, item in TASK_REGISTRY.items()
            ]
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "clean-output":
        root = Path(args.output_dir)
        if root.exists():
            shutil.rmtree(root)
            print(f"已清理输出目录: {root}")
        else:
            print(f"输出目录不存在，无需清理: {root}")
        return 0

    if args.cmd == "preview":
        if args.task not in TASK_REGISTRY:
            raise ValueError(f"未知任务: {args.task}")
        item, base = _task_params(args.task, args.dataset, args.config, args.split)
        preview_fn, _ = _resolve_task_functions(item)
        payload = preview_fn(
            dataset_name=base["dataset_name"],
            config_name=base["config_name"],
            split=base["split"],
            limit=args.limit,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "run":
        if args.task not in TASK_REGISTRY:
            raise ValueError(f"未知任务: {args.task}")
        item, base = _task_params(args.task, args.dataset, args.config, args.split)
        _, run_fn = _resolve_task_functions(item)
        payload = run_fn(
            dataset_name=base["dataset_name"],
            config_name=base["config_name"],
            split=base["split"],
            limit=args.limit if args.limit > 0 else None,
            top_k=args.top_k if args.top_k > 0 else None,
        )
        out = make_output_path(output_dir=args.output_dir, task_name=args.task)
        write_json(out, payload)
        print(f"评测完成，输出: {out}")
        return 0

    if args.cmd == "run-all":
        for task_name, item in TASK_REGISTRY.items():
            _, base = _task_params(task_name, "", "", "")
            _, run_fn = _resolve_task_functions(item)
            payload = run_fn(
                dataset_name=base["dataset_name"],
                config_name=base["config_name"],
                split=base["split"],
                limit=args.limit if args.limit > 0 else None,
                top_k=args.top_k if args.top_k > 0 else None,
            )
            out = make_output_path(output_dir=args.output_dir, task_name=task_name)
            write_json(out, payload)
            print(f"[{task_name}] 完成，输出: {out}")
        return 0

    raise ValueError(f"不支持的命令: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
