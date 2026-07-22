# AI Station Platform Contracts

## Source-Of-Truth Types

The assistant must label the type and observation time of every operational source.

| Type | Answers | Examples |
| :--- | :--- | :--- |
| Knowledge | What is documented or decided? | Markdown, ADRs, runbooks |
| Desired state | What should be deployed? | Terraform, Ansible, Kubernetes manifests |
| Runtime state | What is happening now? | Prometheus, ArgoCD, Proxmox, service health APIs |
| Event history | What recently happened? | Loki, alerts, sanitized exercise timelines |

Knowledge and desired state must never be presented as proof of current runtime health.

## Client Interfaces

### Application API

The versioned REST API owns application workflows, retrieval, status aggregation, citations,
authentication, and policy enforcement. Application clients such as Cordly call this interface.

Initial routes:

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/collections`
- `GET /api/v1/status/documentation`
- `GET /api/v1/status/runtime/homelab`
- `GET /api/v1/status/runtime/homelab/kubernetes`
- `GET /api/v1/status/runtime/ailab/proxmox`
- `POST /api/v1/knowledge/search`
- `POST /api/v1/assistant/ask`

Future routes will separate runtime status from documentation status under explicit paths such as
`/api/v1/status/runtime/homelab`.

The homelab runtime route uses fixed Prometheus queries for observed nodes, maximum CPU, maximum
memory, root disk pressure, down targets, and active alerts. It does not accept caller-supplied
PromQL. Responses include the observation time, source type, limitations, and explicit unavailable
or unconfigured states.

The Kubernetes runtime route returns node readiness, active pod readiness, retained Failed-pod
history, Deployment/StatefulSet/DaemonSet readiness, and ArgoCD Application health/sync state. The
host collector executes fixed `kubectl get` operations and emits a minimized snapshot; kubeconfig,
Secrets, object specifications, logs, and Events are never mounted into the service. Snapshot age is
enforced before the API reports the data as current.

The Proxmox runtime route returns node pressure, storage capacity, and guest inventory from a
host-collected snapshot. A separated `PVEAuditor` token performs only fixed GET requests for the
configured node. The token is never mounted or injected into the API container, and callers cannot
submit arbitrary Proxmox paths or operations.

### OpenAI-Compatible Gateway

LiteLLM provides the authenticated OpenAI-compatible entry point and stable `local-primary`,
`local-fast`, and `local-auto` aliases for the two GPU workers. PostgreSQL-backed virtual keys give
personal, orchestrator, Open WebUI, Codex, Claude, Gemini, and Cordly clients independent model
allowlists and
limits. `local-auto` prefers the B580 and falls back to the B50 after provider failure. The master
key remains administrative only.
Applications that need retrieval, tools, memory, or policy enforcement must call the orchestrator,
not bypass it by calling a raw model endpoint.

The assistant route accepts a question and optional collection allowlist. The application selects
the fixed `local-auto` model route, retrieves bounded knowledge evidence, obtains all fixed runtime
status sources, and validates the model's declared inline evidence IDs before returning an answer.
It does not accept caller-supplied system prompts, model names, infrastructure queries, or tool calls.

### MCP

The remote MCP server will expose the same policy layer through resources and tools:

- Resources: project summaries, decisions, approved documents, and status snapshots.
- Read tools: `search_knowledge`, `get_document`, `list_projects`, and `get_lab_status`.
- Write tools: separate capability and credential scope, disabled initially.

MCP clients never receive direct PostgreSQL, vector store, Prometheus, Proxmox, or filesystem access.

## Citation Contract

Every retrieved result includes:

- collection identifier
- repository-relative path
- heading when available
- starting and ending line
- SHA-256 content hash
- index observation time at the response level

Later generated answers must cite the retrieved evidence used. If evidence is insufficient or stale,
the assistant says so rather than filling the gap from model memory.

## Cordly Contract

Cordly receives a dedicated service identity, model allowlist, rate limit, and data scope. Discord
server creation follows `request -> validated plan -> preview -> approval -> mutation -> audit`.
Cordly does not inherit access to personal notes or administrative lab tools.

## Versioning

- Breaking REST changes require a new `/api/vN` path.
- MCP tool input schemas are versioned before incompatible changes.
- Stable model aliases describe capability, such as `local-chat` or `cloud-reasoning`, rather than
  leaking provider-specific model names into applications.
- Prompt versions and evaluation results are recorded together.
