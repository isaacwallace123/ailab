from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .kubernetes import build_kubernetes_status


def _collect(resource: str, *, namespace: str | None, context: str | None) -> dict[str, Any]:
    command = ["kubectl"]
    if context:
        command.extend(["--context", context])
    command.extend(["get", resource])
    if namespace:
        command.extend(["--namespace", namespace])
    else:
        command.append("--all-namespaces")
    command.extend(["--output", "json"])
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"kubectl could not read {resource}: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect read-only Kubernetes and ArgoCD status.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--context", help="Optional explicit kubectl context")
    arguments = parser.parse_args()

    status = build_kubernetes_status(
        nodes=_collect("nodes", namespace="", context=arguments.context),
        pods=_collect("pods", namespace=None, context=arguments.context),
        deployments=_collect("deployments.apps", namespace=None, context=arguments.context),
        statefulsets=_collect("statefulsets.apps", namespace=None, context=arguments.context),
        daemonsets=_collect("daemonsets.apps", namespace=None, context=arguments.context),
        applications=_collect(
            "applications.argoproj.io", namespace="argocd", context=arguments.context
        ),
        observed_at=datetime.now(UTC),
    )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(f"{arguments.output.suffix}.tmp")
    temporary.write_text(status.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(arguments.output)


if __name__ == "__main__":
    main()
