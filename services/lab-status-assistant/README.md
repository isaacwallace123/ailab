# Lab Status Assistant

The first runnable AI lab service is a read-only, citation-first knowledge API. It safely indexes
an explicit allowlist of repository files, rejects suspected secrets, synchronizes chunks into
PostgreSQL/pgvector, and exposes search and documentation inventory endpoints.

Repository documents deliberately do **not** claim to represent live infrastructure health. The
Prometheus, Kubernetes/ArgoCD, and Proxmox connectors are separate timestamped runtime sources;
sanitized cyberlab connectors remain future work.

The grounded assistant route combines those sources through the scoped LiteLLM `orchestrator`
identity. Generated answers are returned only when their evidence IDs validate against the exact
retrieval and runtime bundle supplied to the model.

## Local development

```powershell
$env:AILAB_SOURCE_CONFIG = 'C:\Users\isaac\Desktop\ailab\config\sources.local.yaml'
uv sync --package lab-status-assistant --extra dev
uv run --package lab-status-assistant uvicorn lab_status_assistant.app:create_app --factory --reload
```

Development mode allows requests without an API token. Set `AILAB_ENVIRONMENT=production` and
`AILAB_API_TOKEN` to exercise the production authentication behavior.

Without `AILAB_DATABASE_URL`, local development uses the in-memory lexical backend. The Compose
deployment uses PostgreSQL full-text search plus 384-dimensional BGE embeddings, an HNSW pgvector
index, and hybrid ranking. The ONNX embedding runtime is CPU-only and its model cache is ignored by
Git. `/api/v1/knowledge/embedding-status` reports configured and embedded chunk counts.

Run the versioned cross-lab retrieval suite against the deployed backend with:

```powershell
.\scripts\evaluate-retrieval.ps1
```

The command fails when an expected source misses its allowed rank, a returned citation does not
match the current index, or an aggregate quality threshold regresses.

Set `AILAB_PROMETHEUS_URL` to enable live homelab status. The connector executes only fixed,
reviewed PromQL expressions and the alerts endpoint; callers cannot submit arbitrary PromQL.
When Docker Desktop cannot route to the LAN, `collect-homelab-status.ps1` writes a timestamped
snapshot and `AILAB_PROMETHEUS_SNAPSHOT_PATH` enables the same status schema with stale-data checks.

`collect-kubernetes-status.ps1` uses the workstation's current kubectl context to collect only
normalized node, pod, controller, and ArgoCD Application status. The kubeconfig stays on the host.
`AILAB_KUBERNETES_SNAPSHOT_PATH` exposes the snapshot with the same explicit stale/unavailable
behavior. Retained Failed pods are reported separately from active controller health so old Evicted
objects do not masquerade as a current outage.

`collect-proxmox-status.ps1` uses a separated `PVEAuditor` API token on the host to collect node
pressure, storage capacity, and guest inventory. The token is read from the ignored `.env`, passed
only to the collector process, and never configured in Compose. The service receives only the
normalized snapshot. Raw PCI/IOMMU discovery remains a separately reviewed root operation.

## API

- `GET /health/live` — process liveness
- `GET /health/ready` — index readiness and source availability
- `GET /api/v1/collections` — indexed collection inventory
- `GET /api/v1/status/documentation` — explicitly non-live repository snapshot
- `GET /api/v1/status/runtime/homelab` — timestamped, read-only Prometheus health signals
- `GET /api/v1/status/runtime/homelab/kubernetes` — Kubernetes and ArgoCD object health
- `GET /api/v1/status/runtime/ailab/proxmox` — Proxmox node, storage, and guest capacity
- `POST /api/v1/knowledge/search` — hybrid search with file and line citations
- `GET /api/v1/knowledge/embedding-status` — hybrid backend and embedding coverage
- `POST /api/v1/assistant/ask` — model-backed synthesis with validated evidence citations
- `GET/POST/DELETE /api/v1/memories` — reviewable explicit durable memory
- `GET /v1/models` — authenticated `ailab-assistant` and `ailab-grounded` discovery
- `POST /v1/chat/completions` — personal conversation, grounded RAG, and explicit memory commands

Open WebUI sends the signed-in account through `X-OpenWebUI-User-Id` and
`X-OpenWebUI-User-Name`. The stable ID scopes durable memories; the display name only personalizes
the current request. Memory endpoints reject requests without an authenticated user ID, and
pre-migration unscoped memories are quarantined under `legacy-unscoped` instead of being exposed
to any current user.

Swagger UI is available at `/docs` in development. Production deployments disable it by default.

The service is CPU-only and does not request a Docker GPU device. The workstation's NVIDIA GPU and
the server's Intel Arc GPUs are intentionally irrelevant to this service's build and runtime.
Inference crosses the authenticated LiteLLM gateway and runs on the server worker selected by
`local-auto`.
