# `ai-core-01` Service VM

Status: **built and serving the accepted AI station on 2026-07-18**.

## Goal

Make the unified AI station continuously available while either GPU worker is benchmarked,
restarted, or rebuilt. The VM and first service migration now implement this deployment contract.

## Placement And Initial Size

| Item | Initial decision |
| :--- | :--- |
| Proxmox host | `cyberlab`, in resource pool `ailab` |
| VM name | `ai-core-01` |
| CPU and memory | 8 vCPU, 16 GiB fixed memory |
| VM identity | VMID `9602`, MAC `BC:24:11:09:A0:47` |
| OS disk | 100 GiB on `local-lvm`, included in VM backups |
| Data disk | None; attach only after filesystem, ownership, capacity, and backup review |
| Network | AI management/LAN only; never cyber attacker or victim bridges |
| Runtime | Ubuntu LTS, Docker Compose, systemd-managed startup |
| Address | Static `192.168.0.221/24`, outside DHCP pool `.100`-`.200` |

## Workload Boundary

| Workload | `ai-core-01` | GPU workers | Homelab k3s |
| :--- | :---: | :---: | :---: |
| LiteLLM policy and aliases | Owns | Backends only | No |
| Open WebUI and chat state | Owns | No | No |
| Lab Status Assistant and MCP | Owns | Model calls only | No |
| PostgreSQL/pgvector and memory | Owns | No | No |
| Model runtimes and GPU drivers | No | Own | No |
| Model cache | Optional cold mirror | Active cache | No |
| Metrics storage and dashboards | Exports metrics | Exports metrics | Existing stack may scrape/display |
| Internal DNS or reviewed ingress | Client | Client | May provide integration |
| Cyberlab telemetry | Sanitized consumer | No | Optional transport only |

## Network Contract

Only the minimum flows should be permitted:

| Source | Destination | Purpose |
| :--- | :--- | :--- |
| Workstation/Tailscale clients | `ai-core-01` HTTPS | Open WebUI, REST, and MCP |
| `ai-core-01` | GPU worker inference ports | LiteLLM model routing |
| `ai-core-01` | approved read-only lab APIs | Proxmox, Prometheus, Kubernetes/Argo CD snapshots |
| Homelab monitoring | AI nodes' metrics endpoints | Scraping only |
| AI nodes | DNS, NTP, approved package/model sources | Controlled egress |

PostgreSQL remains private to the Compose network or loopback. GPU inference ports accept only
`ai-core-01` plus a temporary, explicitly approved workstation maintenance source. No inbound flow
from cyber range networks is allowed.

## State And Backup Evidence

The first build closed the provisioning gate without attaching or formatting a data disk:

- Terraform applied one VM and a final refresh reports no drift. Both Terraform `prevent_destroy`
  and Proxmox `protection=1` are active.
- `backupstore` holds the post-baseline archive from `22:32:42` and the post-service archive from
  `22:58:41`. Both zstd streams pass integrity validation.
- The baseline archive restored successfully into stopped disposable VMID `9699` with a unique MAC;
  its hardware definition was inspected, then only that disposable VM and its temporary volumes
  were removed.
- The Lab Status Assistant pgvector database and Open WebUI PostgreSQL database were copied before
  the old services were retired. Ignored controller dumps remain available for rollback.
- A reboot test returned the guest in 21 seconds; LiteLLM, Open WebUI, PostgreSQL, Docker, pgvector,
  and the Lab Status Assistant recovered automatically and passed the full chat gate.

Remaining operational work is to schedule recurring VM and logical database backups, choose
retention, and copy critical backups to a second physical failure domain.

## Original State And Backup Gate

Before provisioning or migration, record all of the following:

1. Reserve addresses for the pinned VM MACs and publish the DNS names.
2. Choose the authoritative data location and filesystem; document mount ownership and free-space
   alerts.
3. Define backup coverage for PostgreSQL dumps, Open WebUI state, LiteLLM configuration, retrieval
   metadata, and secrets from their external secret store.
4. Define retention and off-host copy location. A snapshot on the same Proxmox storage is not the
   only backup.
5. Restore the database and application state into a disposable target and record the result.

Large model weights and rebuildable indexes may use checksummed manifests and re-download/rebuild
procedures instead of primary backup capacity. User-created knowledge, chat data, configuration,
and database state are not treated as disposable.

## Migration Result

1. VM provisioning, hardening, runtime installation, metrics, firewalling, and protection: complete.
2. LiteLLM/PostgreSQL deployment with real requests through both remote GPU workers: complete.
3. Lab Status Assistant pgvector data, allowlisted sources, embedding cache, and profile migration:
   complete; the workstation reverse tunnel is no longer in the serving path.
4. Open WebUI database migration, login, model visibility, citations, and true streaming: complete.
5. Automatic reboot recovery and post-service backup: complete.
6. The `.101` Open WebUI and LiteLLM services are stopped, disabled, masked, and firewalled; their
   data remains preserved for rollback. Internal DNS, scheduled backup retention, and an observation
   window before deleting that preserved data are still required.

## Acceptance Gates

- A GPU worker reboot does not interrupt the UI, knowledge API, or stored history; only its model
  route becomes unavailable or fails over.
- `ai-core-01` reboot recovery is automatic and produces no manual container startup steps.
- Retrieval v2 remains green and a saved answer retains valid source citations.
- Database backup and restore evidence exists outside the VM being protected.
- Firewall tests reject unapproved LAN sources and all cyber range sources.
- The old deployment remains recoverable until the post-migration observation window closes.
