# AI Lab Roadmap

## Current Priority Queue

These are the highest-priority unfinished items, in order. Phase sections below preserve the full
backlog and acceptance gates but do not override this queue.

1. Stabilize operations around the completed core migration: reserve worker addresses `.101` and
   `.102`, publish internal DNS/TLS for static core `.221`, schedule VM plus logical database backups,
   define retention/off-host copies, and finish the rollback observation window before deleting the
   preserved `.101` application data. Its old UI and gateway are already retired.
2. Make grounded answers dependable: keep the hybrid retrieval gate green and add answer
   correctness, evidence-entailment, adversarial, and latency cases. The evaluated BGE/pgvector
   hybrid backend and the Open WebUI roadmap/follow-up gates now pass.
3. Publish the shared read-only tool plane: expose authenticated Streamable HTTP MCP resources and
   tools for Codex, Claude Code, Gemini, and Open WebUI before considering any write capability.

## Phase 0: Product And Repository Foundation

Status: **complete**.

- Establish the independent AI lab workspace and Git repository.
- Define the product requirements, architecture, ownership, interfaces, and non-goals.
- Accept the VM-first, Compose-first, read-only-first, and federated-control-plane decisions.
- Define data classes, knowledge provenance, explicit memory, and runtime benchmark policy.

## Phase 1: Safe Knowledge API

Status: **in progress; first runnable increment implemented**.

- Read-only, allowlisted repository ingestion: implemented.
- Citation-first lexical search: implemented.
- Production bearer authentication and hardened Compose service: implemented.
- Tests, linting, locked dependencies, and CI: implemented.
- Content-level secret scanning: implemented.
- Persistent PostgreSQL/pgvector schema and incremental chunk synchronization: implemented.
- PostgreSQL full-text search backend: implemented.
- BGE embeddings, typed pgvector storage, HNSW cosine search, and evaluated hybrid retrieval:
  implemented for all indexed chunks.
- Versioned retrieval and citation evaluation set: implemented.
- PostgreSQL lexical baseline recorded (6/6 cases, 1.0 hit rate, 0.833 MRR, 1.0 citation validity).
- Hybrid v2 baseline recorded (13/13 cases, 1.0 hit rate, 0.8846 MRR, 1.0 citation validity).
- Expand adversarial and semantic-only cases and add answer entailment evaluation: next.

Exit gate: indexed content is reproducible, deletable, scoped, secret-scanned, and evaluated.

## Phase 2: First AI Host And Local Runtime

Status: **in progress; both Intel GPU workers and Vulkan baselines operational**.

- CPU, memory, storage, guest, PCI/IOMMU, and reset evidence recorded; network and backup decisions remain.
- Named B50 mapping and scoped mutation token created; clean plan reviewed (1 add, 0 change, 0 destroy).
- Dedicated bridge-scoped `SDN.Use` role added for the privilege-separated Terraform identity.
- AI-owned VMID 9600 created stopped in pool `ailab`; post-apply refresh reports no drift.
- Generated MAC pinned in Terraform so recreation preserves the DHCP identity.
- Guarded Ansible preflight and baseline implemented with SSH hardening and source-restricted UFW.
- Guarded B50-only VFIO first stage passed before the installer was extended to the accepted
  dual-GPU policy with both mappings on `vfio-pci`.
- Ubuntu HWE `7.0.0-28-generic`, guest `xe`, render-node access, and Intel PPA OpenCL/Level Zero/Vulkan
  userspace implemented and validated with a bounded OpenCL compute test.
- Reproducible llama.cpp `b10066` Vulkan build and checksum-pinned 0.6B smoke model implemented.
  B50 prompt/generation benchmarks, deterministic chat, and a localhost-only OpenAI-compatible API
  gate pass; the temporary API service is disabled and stopped after validation.
- Official Qwen3 8B Q4_K_M candidate pinned and benchmarked at 512-token and 4K prompt sizes plus
  128-token generation. Exact schema-constrained JSON and citation-grounded Kubernetes status gates
  pass through a second localhost-only, disabled-at-rest API unit.
- Actual DHCP leases are `192.168.0.101` for node 01 and `192.168.0.102` for node 02; core is static
  at `192.168.0.221`. Reserve stable worker addresses, then finish scheduled backup retention and
  the unused data-disk policy.
- Start with the B50 16 GB while keeping the B580 available for comparison and rollback.
- Expand the Vulkan test to a 7B-14B candidate, then compare llama.cpp SYCL and vLLM XPU.
- Controlled guest shutdown/start GPU reset passed; track the kernel thermal-mailbox warning under
  longer inference workloads.
- B580 mapping and scoped `Mapping.Use` ACL added; VMID 9601 runs with 8 vCPUs, 16 GiB RAM, a
  100 GiB OS disk, and no dedicated data disk.
- Host dual-VFIO policy passed after reboot. `ai-node-01` was reduced from 48 GiB to 32 GiB, keeping
  the two AI VMs at 48 GiB total so cyberlab workloads retain more memory.
- B580 guest HWE `7.0.0-28`, `xe`, OpenCL, Level Zero, Vulkan, llama.cpp smoke/API, and Qwen3 8B
  gates pass. The B580 measured 798.05/552.57 prompt tok/s at 512/4096 tokens and 27.65 generation
  tok/s, materially faster than the B50 in this initial matrix.
- Use separate workers by default (`local-primary` on B50, `local-fast` on B580); benchmark a
  temporary same-VM split only for models that cannot fit one card.
- Select the runtime and initial models from correctness, stability, latency, and resource evidence.
- Add node, container, and GPU health metrics.

Exit gate: one reproducible local model endpoint passes the benchmark and recovery suite.

## Phase 3: Lab Status Assistant

Status: **read-only connectors and grounded local-model synthesis implemented**.

- Prometheus read-only connector with timestamps and fixed queries: implemented.
- ArgoCD and Kubernetes object-state snapshot connector: implemented.
- Deploy kube-state-metrics only if continuous object metrics justify the additional cluster service.
- Proxmox inventory/status through a separated PVEAuditor token: implemented.
- Add sanitized cyberlab status exports without attaching AI services to range networks.
- Model synthesis through `local-auto` with mandatory validated evidence citations: implemented.
- Evaluate stale-data handling, unknown-state behavior, and operational answer quality.

Exit gate: lab questions combine desired state and live state without confusing the two.

## Phase 4: Unified AI Station

Status: **in progress; scoped gateway and chat surface operational**.

- LiteLLM `local-primary`, `local-fast`, and tested `local-auto` fallback, hardened systemd,
  source-restricted UFW, and real-worker route gates: implemented.
- PostgreSQL-backed virtual keys, model allowlists, RPM/TPM/parallel limits, and future-provider
  budget ceilings: implemented for seven client identities.
- CPU-only `ai-core-01`, protected Terraform/Proxmox lifecycle, remote-only GPU routing, Open WebUI
  state migration, local pgvector assistant, automatic reboot recovery, and a verified post-service
  VM backup: implemented.
- Open WebUI with isolated PostgreSQL state, dedicated LiteLLM identity, and closed signup:
  implemented. `ailab-assistant` provides fast personal conversation, automatic grounded lab RAG,
  a private profile, and explicit durable memory; `ailab-grounded` remains the strict evidence-only
  option. Add Speaches for local STT/TTS next.
- Versioned cookbook with model-fit catalog, five role presets, three knowledge packs, six prompts,
  six lazy-loaded skills, four scoped tools, validation, and idempotent Open WebUI sync:
  implemented. Add a portable Markdown editing surface, initially through SilverBullet.
- Explicit preference, project, decision, task, and fact memory is implemented; add portable note,
  project, task, and decision editing workflows.
- Add OpenTelemetry and LLM tracing/evaluation after the core request flow is stable.

Exit gate: chat, voice, and project organization reuse one policy and knowledge layer.

## Phase 5: External Agents And Cordly

Status: **not started**.

- Publish an authenticated Streamable HTTP MCP server with read-only resources and tools.
- Configure scoped access for Codex, Claude Code, and Gemini.
- Give Cordly a dedicated service identity, model allowlist, rate limits, and context boundary.
- Implement plan, validation, preview, approval, mutation, and audit for Discord server changes.
- Add write tools individually only after threat modeling, validation, and recovery tests.

Exit gate: every external client is scoped, observable, revocable, and tested.

## Phase 6: Portfolio And Advanced Workflows

Status: **not started**.

- Publish sanitized architecture, benchmark, evaluation, recovery, and security artifacts.
- Add Wazuh and exercise summarization through sanitized feeds.
- Add reviewed detection and operations drafting workflows.
- Demonstrate failure handling, prompt-injection resistance, and approval-gated actions.
- Keep public demos isolated from private services and data.
