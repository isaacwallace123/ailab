# LiteLLM Model Gateway

## Accepted Topology

LiteLLM `1.92.0` runs as a hardened systemd service on `ai-core-01` and exposes one authenticated,
OpenAI-compatible entry point:

```text
Workstation 192.168.0.138
  -> http://192.168.0.221:4000/v1
     -> local-auto    -> ai-node-02 B580, then ai-node-01 B50 on provider failure
     -> local-primary -> ai-node-01 B50, 192.168.0.101:18090
     -> local-fast    -> ai-node-02 B580, 192.168.0.102:18090
     -> cloud-openai  -> OpenAI API, only when its controller key exists
     -> cloud-claude  -> Anthropic API, only when its controller key exists
     -> cloud-gemini  -> Gemini API, only when its controller key exists
```

All three aliases serve the checksum-pinned Qwen3 8B Q4_K_M model through the pinned llama.cpp
Vulkan runtime. `local-auto` prefers the faster B580 worker and falls back to `local-primary` after
a provider failure. A controlled worker-stop gate proved the B50 fallback before restoring B580
service. Clients use stable aliases and do not need to know worker names, ports, or GPU placement.

## Security Boundary

- UFW permits LiteLLM port 4000 only from the workstation `192.168.0.138/32`.
- Every model request requires either a scoped virtual key or the administrative master key.
- Both workers bind to their VM network, while UFW permits port 18090 only from `ai-core-01`.
- Node 02 temporarily retains its old `.101` source rule for rollback during the observation window.
- Worker servers have no independent LAN authentication because they are not client-reachable.
- LiteLLM and both workers run as unprivileged system users with hardened systemd units.
- LiteLLM uses its own loopback-only PostgreSQL database and isolated database role on the core.
- Prisma engines live under the unprivileged gateway state directory, not under `/root`.
- The master key is reserved for administration; normal scripts default to the `personal` identity.

The controller master key is generated once at `/home/isaac/.config/ailab/litellm-master-key`.
Virtual keys live under `/home/isaac/.config/ailab/litellm-keys/`. All files have mode `0600` and
remain outside Git. Node secrets are stored in `/etc/ailab/litellm.env`, owned by root with mode
`0600`.

Optional upstream keys live under `/home/isaac/.config/ailab/providers/`. The playbook never creates
placeholder provider keys: each cloud alias and its environment entry are rendered only when the
matching secret exists. `personal` and `open-webui` receive access to the enabled cloud aliases while
the other client identities retain their existing local-only allowlists.

## Client Identities

| Identity | Models | RPM | TPM | Parallel | Purpose |
| --- | --- | ---: | ---: | ---: | --- |
| `personal` | all local aliases | 60 | 120,000 | 2 | Isaac's scripts and direct testing |
| `open-webui` | all local aliases | 30 | 120,000 | 2 | Open WebUI backend only |
| `codex` | all local aliases | 20 | 80,000 | 1 | Future Codex integration |
| `claude` | all local aliases | 20 | 80,000 | 1 | Future Claude Code integration |
| `gemini` | all local aliases | 20 | 80,000 | 1 | Future Gemini integration |
| `cordly` | `local-auto` only | 15 | 60,000 | 1 | Future Discord bot service |

Each key also has a 30-day dollar ceiling for future paid providers. The current local llama.cpp
models report zero provider cost, so RPM, TPM, parallelism, and model allowlists are the effective
controls today; the dollar ceilings become meaningful only when priced providers are added.

## Operations

Deploy or reconcile the workers and gateway from WSL:

```bash
cd /mnt/c/Users/isaac/Desktop/ailab/ansible
export ANSIBLE_CONFIG=/mnt/c/Users/isaac/Desktop/ailab/ansible/ansible.cfg
ansible-playbook -i inventory/production/hosts.yml playbooks/litellm.yml
```

Send a request from PowerShell without printing the key:

```powershell
.\scripts\invoke-litellm.ps1 `
  -Model local-auto `
  -Prompt 'Summarize the current Kubernetes status.'
```

Use `-Identity codex`, `claude`, `gemini`, or `cordly` only for that client's integration tests.
Use `-Identity admin` solely for gateway administration.

Service checks:

```bash
systemctl status ailab-litellm.service
systemctl status ailab-llama-worker.service
systemctl status postgresql.service
curl http://127.0.0.1:4000/health/liveliness
```

The core gateway has `onboot=1` and passed a full guest reboot/recovery test. GPU-worker host-start
policy remains a separate availability decision; the UI and stored state recover even if inference
workers are not yet available.

## Remaining Gateway Work

- reserve the current `.101` and `.102` worker DHCP leases and publish stable internal DNS
- evaluate overload and in-flight failure behavior beyond the completed worker-stop fallback gate
- publish metrics to the homelab Prometheus stack
- add TLS/internal DNS before allowing clients beyond the trusted workstation
