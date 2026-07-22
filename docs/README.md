# AI Lab Docs

Documentation for the AI lab workspace.

| File | Contents |
| :--- | :--- |
| [architecture.md](architecture.md) | AI lab purpose, ownership boundary, layers, and starting topology |
| [ai-core-01-plan.md](ai-core-01-plan.md) | Stable CPU-only service VM boundary, network contract, backup gates, and migration order |
| [hardware-and-placement.md](hardware-and-placement.md) | Current two-server hardware inventory, initial AI host recommendation, and migration path |
| [kubernetes-strategy.md](kubernetes-strategy.md) | When to use Proxmox VMs, Docker/systemd, or Kubernetes for AI lab workloads |
| [cross-lab-integration.md](cross-lab-integration.md) | Read-only integration patterns with homelab, cyberlab, and portfolio |
| [security-boundaries.md](security-boundaries.md) | Data classes, AI-specific risks, cyberlab boundaries, and public demo guardrails |
| [operating-model.md](operating-model.md) | Day-to-day operating approach and cross-lab change discipline |
| [roadmap.md](roadmap.md) | Build phases from host/runtime to portfolio-ready demos |
| [product-requirements.md](product-requirements.md) | Users, required capabilities, non-goals, and acceptance criteria |
| [platform-contracts.md](platform-contracts.md) | REST, model gateway, MCP, citations, and Cordly integration contracts |
| [data-governance.md](data-governance.md) | Ingestion, data classes, memory, providers, and tool safety |
| [runtime-benchmark-plan.md](runtime-benchmark-plan.md) | Evidence-driven Intel GPU and runtime selection plan |
| [model-gateway.md](model-gateway.md) | LiteLLM aliases, network boundary, secret handling, and operations |
| [grounded-orchestrator.md](grounded-orchestrator.md) | Evidence-bounded lab questions through the local model gateway |
| [open-webui.md](open-webui.md) | Open WebUI login, scoped gateway connection, security boundary, and operations |
| [retrieval-evaluation.md](retrieval-evaluation.md) | Versioned retrieval quality, ranking, and citation-integrity baseline |
| [assistant-optimization-plan.md](assistant-optimization-plan.md) | Measured streaming baseline and prioritized intelligence, placement, and latency plan |
| [ai-node-01-discovery.md](ai-node-01-discovery.md) | Read-only host discovery facts and the initial VM proposal |
| [gpu-passthrough-runbook.md](gpu-passthrough-runbook.md) | Dual Intel GPU VFIO handoff, validation, guest gates, and rollback |
| [adr/](adr/) | Architecture decision records |

Current control-plane decision: the AI lab starts VM-first and stays AI-owned; Kubernetes and Crossplane are deferred until they solve a concrete service orchestration or platform API problem.
