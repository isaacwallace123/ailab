# ailab

Personal AI lab workspace for local AI infrastructure, model serving, retrieval, agents, evaluation, automation, and AI-assisted operations across the homelab and cyberlab.

This repository is the source of truth for the AI lab only. It should stay separate from the cybersecurity lab and homelab Kubernetes platform, while exposing clean integration points to both.

Portfolio context: this workspace should eventually back `ailab.isaacwallace.dev`. The other lab surfaces can remain distinct:

- `homelab.isaacwallace.dev` for the Kubernetes platform and self-hosted services
- `cyberlab.isaacwallace.dev` for authorized security research and cyber range work
- `ailab.isaacwallace.dev` for local AI systems, demos, agents, and evaluation
- `isaacwallace.dev` as the root portfolio tying the three together

## Status

Current phase: **Phase 4 unified AI station**.

Implemented now:

- Git repository initialized on `main`
- Product requirements, platform contracts, data governance, runtime benchmark plan, and ADRs
- `lab-status-assistant` read-only knowledge API with production bearer authentication
- Allowlisted ingestion across AI lab, homelab, and cyberlab repository sources
- Secret-like filename, path escape, symlink, file type, and file size exclusions
- Search results with collection, path, line, heading, and SHA-256 citations
- Content-level secret detection before indexing
- Persistent PostgreSQL/pgvector schema with incremental chunk synchronization
- PostgreSQL full-text search with an intentionally empty embedding column pending evaluation
- Timestamped Prometheus runtime status using fixed, read-only queries
- Timestamped Kubernetes and ArgoCD object status without containerized cluster credentials
- Timestamped Proxmox node, storage, and guest capacity through a host-only PVEAuditor token
- Hardened Docker Compose service definition
- Locked Python dependencies, unit tests, linting, and CI workflow
- Two Terraform-managed Ubuntu GPU workers with isolated B50 and B580 passthrough
- Pinned llama.cpp Vulkan workers serving checksum-pinned Qwen3 8B
- PostgreSQL-backed LiteLLM gateway with `local-primary`, `local-fast`, and tested `local-auto`
- Scoped identities for personal use, the orchestrator, Open WebUI, Codex, Claude, Gemini, and Cordly
- Open WebUI `0.10.2` with isolated PostgreSQL state, closed signup, and source-restricted UFW
- `ailab-grounded` in Open WebUI with citation-validated cross-lab RAG, runtime evidence, and bounded follow-up context
- Evidence-grounded lab questions through `local-auto` with strict evidence citation validation
- Version-controlled AI cookbook with measured model routes, role presets, knowledge, prompts,
  skills, tools, validation, and idempotent Open WebUI synchronization
- Five installed personal roles for general chat, lab operations, projects, research, and family
  finance education

Prometheus, Kubernetes, ArgoCD, Proxmox, and the cookbook's GitHub integration remain intentionally
read-only; sanitized cyberlab status connectors, MCP, portable knowledge editing, and local speech
are future work.

## Hard Rules

- Do not commit API keys, model provider tokens, SSH keys, private datasets, embeddings, vector databases, Terraform state, or generated model artifacts.
- Do not let AI lab services directly control cyberlab attacker/victim workloads without an explicit reviewed interface.
- Do not expose model APIs, agent UIs, vector databases, or orchestration dashboards directly to the public Internet.
- Do not train, fine-tune, or index private data unless the dataset has a documented source, permission level, retention rule, and deletion path.
- Keep cyberlab offensive tooling, vulnerable targets, and SOC telemetry in the cyberlab unless the AI lab is consuming a sanitized integration feed.

## Architecture Direction

The AI lab should be a service and experimentation layer, not the substrate for every lab.

Recommended split:

| Lab | Primary substrate | Main job |
| :--- | :--- | :--- |
| Homelab | Existing k3s on `pve2` | Shared platform services, GitOps, observability, dashboards, stable apps |
| Cyberlab | Proxmox VMs on `cyberlab` | Isolated attacker, victim, Windows, AD, SOC, packet capture, scenarios |
| AI lab | Proxmox VM(s) plus optional Kubernetes service layer | Model serving, RAG, agents, evals, automations, lab copilots |

Kubernetes should be used where it gives clear operational value: long-running web services, APIs, queues, dashboards, model-serving endpoints, observability, and repeatable deployment.

Kubernetes should not be forced onto every workload. GPU passthrough experiments, large local model runtimes, one-off notebooks, Windows tooling, and cyber range VMs are often simpler and safer as Proxmox VMs.

See:

- [Architecture](docs/architecture.md)
- [`ai-core-01` service VM plan](docs/ai-core-01-plan.md)
- [Hardware and placement](docs/hardware-and-placement.md)
- [Kubernetes strategy](docs/kubernetes-strategy.md)
- [Cross-lab integration](docs/cross-lab-integration.md)
- [Security boundaries](docs/security-boundaries.md)
- [Operating model](docs/operating-model.md)
- [Roadmap](docs/roadmap.md)
- [AI Lab improvement audit](docs/ai-lab-improvement-audit.md)
- [AI Lab cookbook](cookbook/README.md)
- [Product requirements](docs/product-requirements.md)
- [Platform contracts](docs/platform-contracts.md)
- [Data governance](docs/data-governance.md)
- [Runtime benchmark plan](docs/runtime-benchmark-plan.md)
- [LiteLLM model gateway](docs/model-gateway.md)
- [Grounded lab assistant](docs/grounded-orchestrator.md)
- [Retrieval evaluation](docs/retrieval-evaluation.md)
- [Architecture decisions](docs/adr)

## Repository Layout

```text
ansible/       Configuration management for AI lab hosts and services
datasets/      Dataset documentation, manifests, and safe sample fixtures
docs/          Architecture, operations, roadmap, and ADRs
kubernetes/    Future Kubernetes manifests, Helm values, or GitOps apps
models/        Model catalog docs and runtime notes, not large model files
scripts/       Validation and local automation helpers
services/      AI services, APIs, agents, notebooks, and demos
config/        Explicit source allowlists and service configuration
cookbook/      Versioned models, knowledge, prompts, skills, tools, and model-fit catalog
terraform/     Future Proxmox/network/storage infrastructure roots and modules
```

## First Build Targets

1. Keep both Terraform-managed Intel GPU workers reproducible and capacity-aware.
2. Operate the scoped LiteLLM aliases and Open WebUI chat surface.
3. Compare SYCL and vLLM XPU against the accepted dual-GPU Vulkan baseline.
4. Compare embedding candidates against the recorded lexical retrieval baseline before enabling hybrid search.
5. Add sanitized cyberlab status without attaching AI services to range networks.
6. Publish the grounded orchestrator through MCP, then add portable knowledge workflows and voice.

## Suggested Local Workflow

```powershell
cd C:\Users\isaac\Desktop\ailab
```

Keep planning and implementation in this workspace. Cross-lab changes should be made in their own repositories and referenced through documented interfaces rather than copied into this repo.

Install and validate the first service:

```powershell
uv sync --package lab-status-assistant --extra dev
.\scripts\validate.ps1 -SkipContainerConfig
.\scripts\sync-openwebui-workspace.ps1 -DryRun
.\scripts\smoke-test.ps1
```
