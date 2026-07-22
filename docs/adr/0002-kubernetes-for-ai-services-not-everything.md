# ADR 0002: Kubernetes For AI Services, Not Everything

## Status

Accepted

## Context

Isaac wants the homelab, cyberlab, and AI lab to be distinct but able to communicate. A key decision is whether Kubernetes should manage all three labs.

The homelab already uses k3s and ArgoCD successfully. The cyberlab has a documented decision to keep Proxmox VMs as the cyber range substrate and defer Kubernetes until it is useful as a service layer. The AI lab will likely need long-running services, model APIs, retrieval services, dashboards, and background workers, but it may also need VM-level isolation and GPU passthrough.

## Decision

Use Kubernetes selectively.

The homelab remains Kubernetes-first. The cyberlab remains Proxmox-first. The AI lab starts Proxmox-first for host/runtime flexibility and may use Kubernetes for stable AI services when orchestration adds value.

Do not require all three labs to run everything on Kubernetes.

## Consequences

This keeps the operating model practical:

- Kubernetes is used for services that benefit from GitOps, health checks, rollouts, ingress, and observability.
- Proxmox VMs are used for strong isolation, OS-specific workloads, GPU passthrough, and cyber range realism.
- Shared monitoring can still provide one pane of glass across all three labs.
