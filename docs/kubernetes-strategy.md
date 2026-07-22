# Kubernetes Strategy

## Recommendation

Do not use Kubernetes for all three labs as a blanket rule.

Use Kubernetes where it is the right operating model:

- stable web services
- APIs
- background workers
- queues
- dashboards
- observability
- model-serving endpoints that benefit from rollout and health checks
- GitOps-managed internal tools

Use Proxmox VMs where they are the better isolation and lifecycle model:

- cyberlab attacker machines
- vulnerable targets
- Windows and Active Directory
- packet capture and SOC sensor VMs
- GPU passthrough hosts if device scheduling is not needed yet
- one-off notebooks and risky experiments

## Per-Lab Position

| Lab | Kubernetes role |
| :--- | :--- |
| Homelab | Core platform. Keep k3s and ArgoCD as the stable service substrate. |
| Cyberlab | Later service layer only. Keep cyber range workloads as Proxmox VMs. |
| AI lab | Useful service layer. Start with a VM or small namespace; graduate to a dedicated cluster only when needed. |

## Best First Option

Start the AI lab with one Proxmox VM and a small set of services.

Run the first service with Docker Compose or systemd if it is just one host and a few containers. Move to Kubernetes when there are enough services to justify GitOps, service discovery, rollouts, secrets, and observability.

If the existing homelab k3s cluster has enough capacity, AI lab web UIs and lightweight APIs can run there under a separate namespace. Heavy model runtime can remain on `ai-node-01` and be reached internally.

For the current hardware, `ai-node-01` should be planned for the `cyberlab` Proxmox node first.
That node has the RAM, spare storage, and Intel B50 Pro / B580 GPUs. The homelab k3s cluster can
publish dashboards or lightweight UIs later, but it should not be the default place for model
weights, vector stores, GPU runtime experiments, or high-churn indexing jobs.

## When To Create A Dedicated AI Kubernetes Cluster

Create a dedicated AI k3s cluster only when at least two of these are true:

- GPU scheduling matters across more than one node.
- The AI lab has multiple long-running services with independent deploy cycles.
- You need separate failure domains from the homelab.
- You need AI-specific node pools, storage classes, or network policies.
- The homelab cluster becomes noisy or resource constrained.

## Management Model

The efficient model is shared observability, separate ownership:

- Homelab owns core monitoring, dashboards, DNS, ingress, and notification patterns.
- Cyberlab owns its isolated range and security telemetry.
- AI lab owns model runtimes, RAG services, agents, evals, and AI APIs.

Use Grafana dashboards to view all three. Do not collapse all repos into one control plane.

## Control Plane Position

Do not put the AI lab, cyberlab, and homelab under one Kubernetes control plane.

For the AI lab, Kubernetes is a service runtime, not the first infrastructure API. Phase 1 should prove the full AI loop on an AI-owned VM before adding Kubernetes:

- model endpoint
- retrieval store
- lab-status assistant API/UI
- eval set
- metrics and logs visible in homelab Grafana

If the AI lab later gets a Kubernetes cluster, keep it AI-owned. Homelab ArgoCD may deploy AI Kubernetes apps only after an explicit multi-cluster GitOps decision; it should not manage AI VMs, model storage, datasets, or agent permissions.

## Crossplane Position

Defer Crossplane.

Crossplane is worth testing later if the AI lab needs a self-service platform API such as `AINode`, `ModelRuntime`, or `LabService`. It is not the Phase 1 source of truth because the stable resources are not known yet and Terraform/Ansible are simpler for VM lifecycle and host setup.

Sandbox rule: any future Crossplane test should manage one low-risk, non-critical resource first and must not receive broad credentials to cyberlab, homelab, or AI lab infrastructure.

## Practical Path

1. Keep homelab k3s as the stable platform.
2. Keep cyberlab Proxmox-first.
3. Build AI lab on a Proxmox VM first.
4. Add metrics/log forwarding to homelab observability.
5. Add Kubernetes manifests only when the AI service surface grows.
6. Decide later whether AI lab gets its own k3s cluster.

## Initial Runtime Bias

For Phase 1, prefer the simplest runtime that proves the full loop:

- one VM
- one model-serving endpoint
- one retrieval store
- one internal assistant UI/API
- one eval set
- metrics and logs visible from the homelab observability stack

Kubernetes becomes more compelling after there are multiple long-running AI services, separate
deploy cycles, or a real need for GPU scheduling instead of single-VM passthrough.
