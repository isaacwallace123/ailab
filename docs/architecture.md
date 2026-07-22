# AI Lab Architecture

## Purpose

The AI lab exists to build practical local AI systems:

- model serving
- retrieval augmented generation
- agents and automations
- evaluation harnesses
- lab status assistants
- portfolio-safe demos
- AI-assisted SOC and operations workflows

It should be useful to the other labs without becoming their control plane.

## Boundary

The AI lab owns AI-specific infrastructure and code.

It may consume:

- public-safe docs from the portfolio
- selected homelab service metadata
- selected cyberlab status, telemetry summaries, and exercise artifacts

It should not directly own:

- homelab k3s platform resources
- cyberlab attacker or victim machines
- cyberlab gateway firewall policy
- Proxmox cluster baseline configuration outside explicitly declared AI lab resources

## Platform Layers

| Layer | Likely tool | Notes |
| :--- | :--- | :--- |
| Virtualization | Proxmox | AI host VMs, GPU passthrough experiments, isolated notebooks |
| Provisioning | Terraform | VM, storage, DNS, and network declarations when stable |
| Configuration | Ansible | Host packages, runtime setup, users, services |
| Service runtime | Docker Compose first | Kubernetes only after the stable service surface justifies it |
| AI runtimes | llama.cpp and vLLM candidates | Selected by the Intel GPU benchmark, not assumption |
| Model gateway | LiteLLM | OpenAI-compatible aliases, routing, keys, budgets, and limits |
| Orchestration | FastAPI | Retrieval, tools, policies, citations, memory, and application workflows |
| Retrieval | PostgreSQL plus pgvector | Structured metadata and hybrid full-text/vector retrieval |
| Agent access | Streamable HTTP MCP | Scoped resources and tools for Codex, Claude Code, and Gemini |
| User surfaces | Open WebUI, SilverBullet, Speaches | Chat/voice, portable knowledge editing, and local STT/TTS |
| Observability | Prometheus, Grafana, Loki, Alertmanager | Reuse homelab patterns where possible |
| Access | Tailscale, internal DNS, Envoy Gateway | No direct public exposure for private AI endpoints |

## Initial Topology

Recommended Phase 1:

```text
Desktop workspace
  ailab repo

Proxmox node cyberlab
  ai-core-01
    LiteLLM gateway and client policy
    PostgreSQL/pgvector, retrieval, memory, and chat state
    lab-status assistant API/UI and read-only MCP
  ai-node-01
    B50 16 GiB primary/large-context inference worker
  ai-node-02
    B580 12 GiB fast inference and background worker
    embeddings, reranking, voice/vision, and overflow workloads

Homelab k3s
  existing Grafana/Loki/Prometheus
  optional ingress/dashboard surface

Cyberlab
  read-only docs and sanitized telemetry summaries
```

## Naming

Suggested names:

- Resource pool: `ailab`
- Management network: `ai-mgmt`
- First host: `ai-node-01`
- Fast worker: `ai-node-02`
- First service: `lab-status-assistant`
- Future namespace: `ai-lab`

Do not assign final IP ranges until the current Proxmox/LAN/VLAN layout is reviewed.

## Hardware Placement

The likely first host is the `cyberlab` Proxmox node because it has 128 GB RAM, spare SSD/NVMe
capacity, and two AI-capable GPUs: Intel B50 Pro 16 GB and Intel B580 12 GB. The homelab server
should remain focused on personal services, NAS/media, k3s, and Plex transcoding through the
Intel Arc A380.

The accepted target assigns one GPU per worker VM: 32 GiB system RAM and the B50 for `ai-node-01`,
plus 16 GiB and the B580 for `ai-node-02`. A CPU-only `ai-core-01` VM owns LiteLLM, Open WebUI,
PostgreSQL/pgvector, orchestration, retrieval, memory, and MCP so GPU maintenance cannot take down
the durable service plane. LiteLLM exposes stable aliases while keeping physical placement out of
client applications. See [`ai-core-01` Service VM Plan](ai-core-01-plan.md).

The stable gateway, Open WebUI, PostgreSQL/pgvector, and Lab Status Assistant now run on
`ai-core-01`. `local-primary` and `local-fast` reach the B50 and B580 workers through
source-restricted UFW rules; `local-auto` prefers the B580 and has a tested B50 fallback. A
loopback-only PostgreSQL service backs scoped identities, chat state, retrieval, and memory. Port
4000 and Open WebUI remain limited to the workstation until TLS and internal DNS are implemented.

See [Hardware and placement](hardware-and-placement.md) for the detailed inventory and migration
plan.

## First Service Shape

The implemented first service is `lab-status-assistant`.

Initial responsibilities:

- ingest only allowlisted Markdown/YAML/JSON/Terraform metadata from the three labs
- return repository-relative citations with lines and content hashes
- authenticate production requests and mount all sources read-only
- identify documentation snapshots as non-live state
- keep all cross-lab actions read-only until a reviewed write interface exists

The next increments add evaluated embeddings and hybrid retrieval, model-backed synthesis, answer
quality evaluations, and MCP without changing this provenance contract.
