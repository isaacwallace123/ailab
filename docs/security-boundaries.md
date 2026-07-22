# Security Boundaries

## Defaults

Treat AI lab services as internal systems. They may contain prompts, tool traces, embeddings, documents, logs, API keys, and generated outputs that should not be public.

Default stance:

- private network first
- Tailscale or internal LAN access
- no direct public model APIs
- no direct public vector database
- no direct public agent runner
- no secret-bearing logs in Git

## Data Classes

| Class | Examples | Rule |
| :--- | :--- | :--- |
| Public | portfolio copy, public docs, demo screenshots | Can be published after review |
| Internal | lab topology, private hostnames, local IPs, runbooks | Keep private unless intentionally summarized |
| Sensitive | API keys, passwords, private prompts, raw logs, embeddings, datasets | Never commit or publish |
| Cyber-sensitive | exploit traces, packet captures, attacker notes, vulnerable endpoints | Keep in cyberlab or sanitized exports |

## AI-Specific Risks

- Embeddings can leak source data.
- Tool-using agents can mutate systems faster than intended.
- Logs may capture prompts, secrets, URLs, and private infrastructure details.
- Provider APIs may retain or process submitted data depending on account settings and product terms.
- Local models still need access control if they expose HTTP endpoints.

## Guardrails

- Keep `.env` files untracked.
- Keep model weights and dataset caches untracked.
- Document every dataset before indexing it.
- Prefer read-only tokens for cross-lab status collection.
- Require explicit review before any AI agent writes to another lab.
- Keep public demos backed by mock or sanitized data unless deliberately approved.
- Keep GPU runtime logs, prompts, embeddings, and generated artifacts out of Git by default.
- Treat cross-lab document indexes as derived sensitive data unless they are built only from explicitly public sources.
- Keep lab synthesis behind the authenticated application API and a dedicated LiteLLM identity.
- Treat retrieved text as untrusted data, keep model/system selection server-side, and reject
  fabricated or conflicting evidence identifiers before returning generated answers.
- Keep production Open WebUI, the assistant API, PostgreSQL, and LiteLLM on `ai-core-01` service-local
  paths; do not reintroduce workstation SSH bridges or widen worker firewalls for production traffic.
- Treat Open WebUI Workspace Tool source as privileged server code. Keep it reviewed, narrow, and
  read-only until an isolated authenticated MCP tool plane is available.

## Cyberlab Boundary

The cyberlab is intentionally isolated. The AI lab can help interpret cyberlab outputs, but it should not become a hidden command channel into attacker or victim networks.

Allowed early integrations:

- read-only docs
- sanitized reports
- copied exercise timelines
- limited API pulls from approved dashboards

Deferred integrations:

- automated exploit execution
- automated firewall changes
- direct control of scenario lifecycle
- direct access to vulnerable target networks

## Hardware Boundary

The first AI lab host may share the physical `cyberlab` server. That does not permit the AI lab to
attach services to cyberlab attacker/victim bridges or inherit cyberlab credentials. AI services
should use a dedicated AI network or tightly scoped LAN path, and any telemetry crossing from
cyberlab into AI lab should be sanitized first.
