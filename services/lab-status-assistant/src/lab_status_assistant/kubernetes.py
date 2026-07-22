from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    ArgoApplicationStatus,
    KubernetesRuntimeStatus,
    RuntimeIssue,
    RuntimeSignal,
)


def _items(payload: dict[str, Any], resource: str) -> list[dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"kubectl returned invalid {resource} data")
    return items


def _metadata(item: dict[str, Any]) -> tuple[str | None, str]:
    metadata = item.get("metadata", {})
    return metadata.get("namespace"), str(metadata.get("name", "unknown"))


def _controller_signal(
    *,
    items: list[dict[str, Any]],
    kind: str,
    desired_field: str,
    ready_field: str,
    updated_field: str,
    issues: list[RuntimeIssue],
) -> RuntimeSignal:
    ready_count = 0
    for item in items:
        namespace, name = _metadata(item)
        spec = item.get("spec", {})
        status = item.get("status", {})
        desired = int(status.get(desired_field, spec.get("replicas", 1)) or 0)
        ready = int(status.get(ready_field, 0) or 0)
        updated = int(status.get(updated_field, ready) or 0)
        if ready >= desired and updated >= desired:
            ready_count += 1
        else:
            issues.append(
                RuntimeIssue(
                    kind=kind,
                    severity="critical" if desired > 0 and ready == 0 else "warning",
                    namespace=namespace,
                    name=name,
                    summary=f"{ready}/{desired} ready and {updated}/{desired} updated.",
                )
            )

    total = len(items)
    return RuntimeSignal(
        name=f"ready_{kind.lower()}s",
        state="healthy" if ready_count == total else "warning",
        value=float(ready_count),
        unit=kind.lower() + "s",
        detail=f"{ready_count} of {total} {kind.lower()}s satisfy desired readiness.",
    )


def build_kubernetes_status(
    *,
    nodes: dict[str, Any],
    pods: dict[str, Any],
    deployments: dict[str, Any],
    statefulsets: dict[str, Any],
    daemonsets: dict[str, Any],
    applications: dict[str, Any],
    observed_at: datetime | None = None,
) -> KubernetesRuntimeStatus:
    node_items = _items(nodes, "node")
    pod_items = _items(pods, "pod")
    deployment_items = _items(deployments, "deployment")
    statefulset_items = _items(statefulsets, "statefulset")
    daemonset_items = _items(daemonsets, "daemonset")
    application_items = _items(applications, "ArgoCD Application")
    issues: list[RuntimeIssue] = []

    ready_nodes = 0
    for item in node_items:
        _, name = _metadata(item)
        conditions = item.get("status", {}).get("conditions", [])
        ready = next(
            (
                condition.get("status")
                for condition in conditions
                if condition.get("type") == "Ready"
            ),
            "Unknown",
        )
        if ready == "True":
            ready_nodes += 1
        else:
            issues.append(
                RuntimeIssue(
                    kind="Node",
                    severity="critical",
                    name=name,
                    summary=f"Ready condition is {ready}.",
                )
            )

    failed_reasons: Counter[str] = Counter()
    failed_examples: dict[str, list[str]] = {}
    running_pods = 0
    active_unhealthy_pods = 0
    for item in pod_items:
        namespace, name = _metadata(item)
        status = item.get("status", {})
        phase = str(status.get("phase", "Unknown"))
        if phase == "Running":
            running_pods += 1
            not_ready = [
                str(container.get("name", "unknown"))
                for container in status.get("containerStatuses", [])
                if not container.get("ready", False)
            ]
            if not_ready:
                active_unhealthy_pods += 1
                issues.append(
                    RuntimeIssue(
                        kind="Pod",
                        severity="warning",
                        namespace=namespace,
                        name=name,
                        summary="Running with unready containers: " + ", ".join(not_ready[:3]),
                    )
                )
        elif phase == "Failed":
            reason = str(status.get("reason") or "Unknown")
            failed_reasons[reason] += 1
            failed_examples.setdefault(reason, [])
            if len(failed_examples[reason]) < 3:
                failed_examples[reason].append(f"{namespace}/{name}")
        elif phase not in {"Succeeded"}:
            active_unhealthy_pods += 1
            issues.append(
                RuntimeIssue(
                    kind="Pod",
                    severity="warning",
                    namespace=namespace,
                    name=name,
                    summary=f"Pod phase is {phase}.",
                )
            )

    for reason, count in sorted(failed_reasons.items()):
        examples = ", ".join(failed_examples[reason])
        issues.append(
            RuntimeIssue(
                kind="FailedPodHistory",
                severity="warning",
                count=count,
                summary=f"{count} retained Failed pods report {reason}. Examples: {examples}.",
            )
        )

    controller_signals = [
        _controller_signal(
            items=deployment_items,
            kind="Deployment",
            desired_field="replicas",
            ready_field="availableReplicas",
            updated_field="updatedReplicas",
            issues=issues,
        ),
        _controller_signal(
            items=statefulset_items,
            kind="StatefulSet",
            desired_field="replicas",
            ready_field="readyReplicas",
            updated_field="updatedReplicas",
            issues=issues,
        ),
        _controller_signal(
            items=daemonset_items,
            kind="DaemonSet",
            desired_field="desiredNumberScheduled",
            ready_field="numberReady",
            updated_field="updatedNumberScheduled",
            issues=issues,
        ),
    ]

    application_statuses: list[ArgoApplicationStatus] = []
    healthy_applications = 0
    synced_applications = 0
    for item in application_items:
        _, name = _metadata(item)
        spec = item.get("spec", {})
        status = item.get("status", {})
        health = str(status.get("health", {}).get("status", "Unknown"))
        sync = str(status.get("sync", {}).get("status", "Unknown"))
        if health == "Healthy":
            healthy_applications += 1
        if sync == "Synced":
            synced_applications += 1
        if health != "Healthy" or sync != "Synced":
            issues.append(
                RuntimeIssue(
                    kind="ArgoApplication",
                    severity="critical" if health in {"Degraded", "Missing"} else "warning",
                    namespace="argocd",
                    name=name,
                    summary=f"Health is {health}; sync is {sync}.",
                )
            )
        application_statuses.append(
            ArgoApplicationStatus(
                name=name,
                project=str(spec.get("project", "default")),
                destination_namespace=spec.get("destination", {}).get("namespace") or None,
                health=health,
                sync=sync,
                reconciled_at=status.get("reconciledAt") or None,
            )
        )

    node_count = len(node_items)
    failed_count = sum(failed_reasons.values())
    application_count = len(application_items)
    signals = [
        RuntimeSignal(
            name="ready_nodes",
            state="healthy" if ready_nodes == node_count and node_count > 0 else "critical",
            value=float(ready_nodes),
            unit="nodes",
            detail=f"{ready_nodes} of {node_count} Kubernetes nodes report Ready.",
        ),
        RuntimeSignal(
            name="running_pods",
            state="healthy" if active_unhealthy_pods == 0 else "warning",
            value=float(running_pods),
            unit="pods",
            detail=f"{active_unhealthy_pods} active pods are Pending, Unknown, or not ready.",
        ),
        RuntimeSignal(
            name="retained_failed_pods",
            state="healthy" if failed_count == 0 else "warning",
            value=float(failed_count),
            unit="pods",
            detail="Failed pods may be historical; controller readiness determines active impact.",
        ),
        *controller_signals,
        RuntimeSignal(
            name="healthy_argocd_applications",
            state="healthy" if healthy_applications == application_count else "warning",
            value=float(healthy_applications),
            unit="applications",
            detail=f"{healthy_applications} of {application_count} applications report Healthy.",
        ),
        RuntimeSignal(
            name="synced_argocd_applications",
            state="healthy" if synced_applications == application_count else "warning",
            value=float(synced_applications),
            unit="applications",
            detail=f"{synced_applications} of {application_count} applications report Synced.",
        ),
    ]

    if any(issue.severity == "critical" for issue in issues):
        overall_state = "critical"
    elif issues:
        overall_state = "warning"
    else:
        overall_state = "healthy"

    return KubernetesRuntimeStatus(
        state=overall_state,
        source="kubectl",
        observed_at=observed_at or datetime.now(UTC),
        signals=signals,
        applications=sorted(application_statuses, key=lambda app: app.name),
        issues=issues,
        limitations=[
            "This read-only snapshot contains object status, not logs or Kubernetes Events.",
            "Retained Failed pods are warnings unless current nodes or controllers are unhealthy.",
            "The collector does not mutate Kubernetes or ArgoCD resources.",
        ],
    )


class KubernetesSnapshotConnector:
    def __init__(self, snapshot_path: Path, *, max_age_seconds: float = 120.0) -> None:
        self.snapshot_path = snapshot_path
        self.max_age_seconds = max_age_seconds

    def status(self) -> KubernetesRuntimeStatus:
        now = datetime.now(UTC)
        try:
            snapshot = KubernetesRuntimeStatus.model_validate_json(
                self.snapshot_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return KubernetesRuntimeStatus(
                state="unavailable",
                source="kubernetes-snapshot",
                observed_at=now,
                signals=[],
                applications=[],
                issues=[],
                limitations=["The Kubernetes snapshot is missing or invalid."],
                error="No valid Kubernetes runtime snapshot is available.",
            )

        age_seconds = (now - snapshot.observed_at).total_seconds()
        limitations = [
            *snapshot.limitations,
            "Docker Desktop consumes a host-collected read-only kubectl snapshot.",
        ]
        if age_seconds > self.max_age_seconds:
            return snapshot.model_copy(
                update={
                    "state": "unavailable",
                    "source": "kubernetes-snapshot",
                    "limitations": [
                        *limitations,
                        f"The snapshot is stale by policy ({age_seconds:.0f} seconds old).",
                    ],
                    "error": "The Kubernetes runtime snapshot is stale.",
                }
            )
        return snapshot.model_copy(
            update={"source": "kubernetes-snapshot", "limitations": limitations}
        )
