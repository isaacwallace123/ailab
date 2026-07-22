#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_catalog(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Model cookbook must be a version 1 mapping.")
    return payload


def recommend(catalog: dict, task: str, worker: str | None, include_candidates: bool) -> list[dict]:
    workers = catalog.get("workers", {})
    selected_workers = {worker: workers[worker]} if worker else workers
    recommendations = []
    for model in catalog.get("models", []):
        if task not in model.get("tasks", []):
            continue
        if model.get("status") != "active" and not include_candidates:
            continue
        route = catalog.get("routes", {}).get(model.get("route"), {})
        preferred = model.get("preferred_worker") or route.get("worker")
        for worker_id, hardware in selected_workers.items():
            if preferred and worker_id != preferred:
                continue
            required = float(model.get("required_vram_gib", 0))
            available = float(hardware.get("vram_gib", 0))
            if required > available:
                continue
            status_score = 100 if model.get("status") == "active" else 25
            speed = float(model.get("measured_generation_tokens_per_second", 0))
            headroom = available - required
            recommendations.append(
                {
                    "model": model["id"],
                    "status": model["status"],
                    "route": model.get("route"),
                    "worker": worker_id,
                    "gpu": hardware.get("gpu"),
                    "required_vram_gib": required,
                    "vram_headroom_gib": headroom,
                    "measured_generation_tokens_per_second": speed or None,
                    "promotion_gates": model.get("promotion_gates", []),
                    "score": round(status_score + speed + min(headroom, 16) / 10, 3),
                }
            )
    return sorted(recommendations, key=lambda item: (-item["score"], item["model"]))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Inspect the AI Lab hardware-aware model cookbook."
    )
    parser.add_argument("--catalog", type=Path, default=repo_root / "cookbook/catalog/models.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="Print the complete catalog as JSON.")
    recommend_parser = subparsers.add_parser("recommend", help="Recommend models for a task.")
    recommend_parser.add_argument("--task", required=True)
    recommend_parser.add_argument("--worker")
    recommend_parser.add_argument("--include-candidates", action="store_true")
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    if args.command == "list":
        print(json.dumps(catalog, indent=2))
        return 0
    if args.worker and args.worker not in catalog.get("workers", {}):
        parser.error(f"Unknown worker: {args.worker}")
    results = recommend(catalog, args.task, args.worker, args.include_candidates)
    print(json.dumps({"task": args.task, "recommendations": results}, indent=2))
    return 0 if results else 2


if __name__ == "__main__":
    raise SystemExit(main())
