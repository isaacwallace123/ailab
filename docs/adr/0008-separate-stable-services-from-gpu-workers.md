# ADR 0008: Separate Stable Services From GPU Workers

## Status

Accepted

## Context

The first working AI station placed LiteLLM, Open WebUI, PostgreSQL, and orchestration beside the
B50 inference runtime on `ai-node-01`. That was the shortest path to a validated end-to-end system,
but it couples chat and knowledge availability to GPU driver experiments, runtime rebuilds, model
memory pressure, and worker reboots.

The homelab k3s cluster is already responsible for personal services and is under Longhorn disk
pressure. Moving AI state there now would increase its failure domain and make the AI lab dependent
on a platform it does not own. The development workstation is also not an appropriate permanent
service host.

## Decision

Create a CPU-only Proxmox VM named `ai-core-01` in the `ailab` resource pool. It owns the stable AI
control and data plane:

- LiteLLM gateway and client policy
- Open WebUI and its database
- Lab Status Assistant REST API and future read-only MCP endpoint
- PostgreSQL/pgvector, retrieval ingestion, and explicit memory
- optional SilverBullet, Speaches CPU components, and telemetry collectors after separate review

Keep `ai-node-01` and `ai-node-02` as replaceable inference workers. They own GPU drivers, model
runtimes, local model caches, and worker-level metrics, and expose source-restricted inference
endpoints to `ai-core-01`. They do not own shared chat history, retrieval state, client identities,
or the only copy of service configuration.

Start `ai-core-01` at 8 vCPU, 16 GiB fixed memory, and a 100 GiB OS disk. Final addressing and any
dedicated data disk remain blocked on DHCP reservation, filesystem, capacity, and backup/restore
decisions. Do not create the VM or migrate state until those gates are recorded and a rollback
backup has been restore-tested.

The homelab k3s cluster may scrape metrics, display dashboards, and provide reviewed DNS or ingress
integration. It does not host the authoritative AI databases or gateway in this phase. The cyberlab
may provide sanitized read-only exports only; AI services never attach to attacker or victim
networks.

## Consequences

GPU workers can be rebuilt or restarted without taking down the user-facing AI station or losing
state. The stable service VM has a clear backup unit and can later move to dedicated AI hardware.
This adds one VM and a controlled state migration, and it does not provide physical high
availability because all three VMs initially share the same Proxmox host.

