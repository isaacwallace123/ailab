# Hardware And Placement

## Purpose

The AI lab needs to be planned as its own project even though it will probably share the current cyberlab server at first. This document captures the physical hardware, the temporary sharing model, and the migration path to a dedicated AI server later.

## Current Physical Servers

| Server | Primary role now | AI relevance |
| :--- | :--- | :--- |
| Homelab server / `pve2` | Personal services, k3s, NAS/media, Plex | Useful for lightweight AI UIs, dashboards, observability, and read-only integration surfaces |
| Cyberlab server / `cyberlab` | Cyber range VMs, SOC, scenarios, future Windows/AD | Best initial host for AI services because it has spare storage, high RAM, and two GPUs |

## Development Workstation

The Windows development workstation runs Docker Desktop and has an NVIDIA GPU. It is a development
and integration environment, not the production inference benchmark target.

- CPU-only APIs, tests, UIs, retrieval, and container integration may run locally.
- The NVIDIA GPU may later provide a disposable development model endpoint.
- NVIDIA results must not be used to select or tune the server runtime.
- Production inference remains targeted at the Intel Arc Pro B50/B580 server and must pass the Intel
  SYCL/Vulkan/XPU benchmark.
- Compose services receive no GPU device request unless a separate development profile explicitly
  adds one.

## Homelab Server Inventory

This server is for personal-use cases first.

| Component | Role |
| :--- | :--- |
| AMD Ryzen 5 5600 | Homelab compute |
| 64 GB DDR4 Corsair Vengeance CL16 3200 MHz | k3s and VM memory |
| 8 TB HDD | NAS/media capacity |
| 500 GB NVMe | Fast local storage |
| 500 GB SATA SSD | Secondary fast local storage |
| Intel Arc A380 | Plex hardware transcoding |

AI lab should not assume this host is available for heavy model serving. It can use the homelab platform for observability, ingress patterns, dashboards, or small internal services if explicitly documented.

## Cyberlab / AI-Capable Server Inventory

This server is the practical first placement for AI lab workloads.

| Component | Role / opportunity |
| :--- | :--- |
| Intel Core i7-13700KF | Strong CPU for orchestration, ingestion, indexing, eval workers, and CPU fallback inference |
| 128 GB DDR4 Corsair Vengeance CL16 3200 MHz | Enough memory for several VMs, RAG services, databases, and moderate local models |
| 1 TB Seagate FireCuda 530 NVMe | Current Proxmox OS and persistent VM datastore; avoid overloading with AI churn |
| 1 TB WD Black SN770 NVMe | Currently assigned to disposable cyber scenarios; do not reassign before a free-capacity and ownership review |
| 960 GB Micron SATA SSD | Currently assigned to Windows/templates/bulk storage; possible AI capacity only after a free-space review |
| 2 TB Seagate Barracuda Compute HDD | Candidate for cold datasets, exports, backups, recordings, and large generated artifacts |
| Intel Arc Pro B50 GPU, 16 GB VRAM | Primary AI GPU candidate |
| Intel B580 Battlemage Founders GPU, 12 GB VRAM | Secondary AI GPU candidate or separate inference/experimentation device |

The GPUs should be considered AI lab capacity by default. Cyberlab GPU use should be deliberate and temporary, for example password-cracking demos or GPU telemetry experiments, because the AI lab will need predictable access.

## Initial Placement Recommendation

Use two lean AI worker VMs plus one CPU-only stable service VM on the `cyberlab` Proxmox node. This
lets both GPUs serve concurrently while keeping shared state available during worker maintenance and
preserving RAM for the cyber range.

Suggested shape for Phase 1 planning:

| Resource | Starting point |
| :--- | :--- |
| VM name | `ai-node-01` / `ai-node-02` |
| Resource pool | `ailab` |
| CPU | 12 vCPU / 8 vCPU |
| Memory | 32 GiB / 16 GiB fixed, 48 GiB total |
| Storage | 100 GiB OS each; node 01 retains the unformatted 500 GiB data disk |
| GPU | B50 16 GiB / B580 12 GiB through separate named PCI mappings |
| Network | dedicated AI management network or tightly scoped LAN access; no direct attachment to cyberlab attacker/victim bridges |

The accepted `ai-core-01` VM runs at 8 vCPU, 16 GiB fixed memory, and a 100 GiB OS disk. It
owns the gateway, UI, databases, retrieval/orchestration, and future read-only MCP service. The GPU
VMs are replaceable inference workers. The initial backup and restore gate passed; permanent
addressing, scheduled retention, and a second physical backup domain remain open. See
[`ai-core-01` Service VM](ai-core-01-plan.md).

This gives the AI lab independent worker boundaries while preserving a clean migration path. If a
later dedicated AI server arrives, migrate the workers, model storage, vector stores, and service
configs without restructuring the homelab or cyberlab.

## What Belongs Where

| Workload | Recommended home |
| :--- | :--- |
| Model serving | AI lab VM first; Kubernetes later if service count justifies it |
| RAG API and lab status assistant | AI lab repo, possibly served through homelab ingress after review |
| Vector database | AI lab VM or AI-owned storage |
| Evals and benchmark jobs | AI lab VM; avoid starving cyberlab scenarios |
| Grafana dashboards | homelab observability stack can display AI lab metrics |
| Cyber attack execution | cyberlab only |
| Cyber telemetry summarization | AI lab can consume sanitized exports |
| Portfolio demo | portfolio repo, backed by sanitized AI lab outputs |

## Accepted Build Evidence And Remaining Decisions

1. Both GPU PCI IDs, isolated IOMMU groups, reset interfaces, mappings, and VFIO ownership pass.
2. VMID 9600 has the B50; VMID 9601 has the B580; both use `vmbr0` only and source-restricted UFW.
3. Pinned llama.cpp Vulkan and Qwen3 8B correctness/performance gates pass on both cards.
4. SYCL and vLLM XPU comparisons remain before the permanent inference runtime decision.
5. VMID 9602 and the stable services are operational on static `.221`. GPU-worker DHCP
   reservations, scheduled/off-host backup retention, and the unused node-01 data-disk policy remain
   open.

Docker Compose and the initial source allowlist are now accepted and implemented for the first
service. Kubernetes remains deferred until multiple stable AI services justify it.

## Separation Plan

The AI lab should remain portable:

- keep Terraform, Ansible, Kubernetes manifests, model docs, service code, and evals in `ailab`
- use explicit names such as `ailab`, `ai-node-01`, and `lab-status-assistant`
- do not store cyberlab secrets, attack payloads, raw packet captures, or private homelab data in AI indexes
- store large model files and datasets outside Git with documented paths and retention rules
- make every cross-lab integration read-only until there is a reviewed write interface
