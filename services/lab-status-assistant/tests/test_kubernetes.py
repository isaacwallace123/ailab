from datetime import UTC, datetime, timedelta
from pathlib import Path

from lab_status_assistant.kubernetes import KubernetesSnapshotConnector, build_kubernetes_status


def _list(*items):
    return {"apiVersion": "v1", "kind": "List", "items": list(items)}


def _healthy_status():
    return build_kubernetes_status(
        nodes=_list(
            {
                "metadata": {"name": "node-1"},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        ),
        pods=_list(
            {
                "metadata": {"namespace": "apps", "name": "web-1"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [{"name": "web", "ready": True}],
                },
            }
        ),
        deployments=_list(
            {
                "metadata": {"namespace": "apps", "name": "web"},
                "spec": {"replicas": 1},
                "status": {"replicas": 1, "availableReplicas": 1, "updatedReplicas": 1},
            }
        ),
        statefulsets=_list(),
        daemonsets=_list(),
        applications=_list(
            {
                "metadata": {"name": "web"},
                "spec": {"project": "apps", "destination": {"namespace": "apps"}},
                "status": {
                    "health": {"status": "Healthy"},
                    "sync": {"status": "Synced"},
                    "reconciledAt": "2026-07-18T05:00:00Z",
                },
            }
        ),
    )


def test_healthy_objects_produce_healthy_status() -> None:
    status = _healthy_status()

    assert status.state == "healthy"
    assert status.applications[0].health == "Healthy"
    assert not status.issues


def test_failed_history_is_warning_but_degraded_application_is_critical() -> None:
    healthy = _healthy_status()
    status = build_kubernetes_status(
        nodes=_list(
            {
                "metadata": {"name": "node-1"},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        ),
        pods=_list(
            {
                "metadata": {"namespace": "apps", "name": "old-web"},
                "status": {"phase": "Failed", "reason": "Evicted"},
            }
        ),
        deployments=_list(),
        statefulsets=_list(),
        daemonsets=_list(),
        applications=_list(
            {
                "metadata": {"name": "web"},
                "spec": {"project": "apps", "destination": {"namespace": "apps"}},
                "status": {
                    "health": {"status": "Degraded"},
                    "sync": {"status": "OutOfSync"},
                },
            }
        ),
        observed_at=healthy.observed_at,
    )

    assert status.state == "critical"
    failed_history = next(issue for issue in status.issues if issue.kind == "FailedPodHistory")
    assert failed_history.severity == "warning"
    assert failed_history.count == 1
    assert any(issue.kind == "ArgoApplication" for issue in status.issues)


def test_snapshot_connector_rejects_stale_status(tmp_path: Path) -> None:
    stale = _healthy_status().model_copy(
        update={"observed_at": datetime.now(UTC) - timedelta(minutes=5)}
    )
    snapshot_path = tmp_path / "kubernetes.json"
    snapshot_path.write_text(stale.model_dump_json(), encoding="utf-8")

    status = KubernetesSnapshotConnector(snapshot_path, max_age_seconds=120).status()

    assert status.state == "unavailable"
    assert status.error == "The Kubernetes runtime snapshot is stale."
