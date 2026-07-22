# ADR 0003: Federated Lab Control Planes

## Status

Accepted

## Context

The homelab, cyberlab, and AI lab share hardware during the current build phase, and more servers may be added later. It is tempting to put every lab under one Kubernetes control plane, but the labs have different security, lifecycle, and workload needs.

The homelab already has a mature k3s and ArgoCD platform. The cyberlab needs VM-level isolation for attacker, victim, Windows, AD, SOC, packet capture, and disposable scenario workloads. The AI lab needs GPU-capable model runtime flexibility before it needs Kubernetes orchestration.

## Decision

Use federated control planes with shared platform standards.

The AI lab starts with an AI-owned Proxmox VM, likely `ai-node-01`, and uses Docker Compose or systemd for the first service. Kubernetes becomes an AI service layer only after there are multiple stable services, independent deploy cycles, or GPU scheduling needs.

Homelab observability, dashboard, ingress, and catalog patterns may be reused, but the AI lab remains the owner of AI model runtimes, vector stores, datasets, agents, evals, and generated artifacts.

Crossplane is deferred. It may be tested later as a platform API experiment, but it is not the Phase 1 infrastructure source of truth.

## Consequences

- AI services can move to dedicated hardware later without changing ownership.
- Homelab remains the shared operations view, not the AI control plane.
- Cyberlab isolation decisions remain intact.
- Cross-lab integrations must be read-only until a reviewed write interface exists.
