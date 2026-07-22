# Grounded Lab Assistant

The Lab Status Assistant combines approved repository retrieval with the three existing read-only
runtime snapshots and sends that bounded evidence to LiteLLM's `local-auto` route. It answers
through `POST /api/v1/assistant/ask` and never gives callers direct model, prompt, PromQL,
Kubernetes, Proxmox, database, or filesystem control.

## Request flow

1. Authenticate the application request with the Lab Status Assistant bearer token.
2. Search only the allowlisted AI lab, homelab, and cyberlab collections.
3. Read the fixed Prometheus, Kubernetes/ArgoCD, and Proxmox status connectors.
4. Label repository chunks as knowledge and connector results as runtime evidence.
5. Send the bounded evidence to `local-auto` with the scoped `orchestrator` LiteLLM identity.
6. Accept the model output only when every declared citation is supplied evidence. The application
   adds an evidence footer when the local model supplies valid structured IDs but omits prose markers;
   partial, conflicting, and fabricated citations are rejected.

Repository evidence can explain documented architecture or desired state. It cannot support a
claim that infrastructure is currently healthy. Runtime evidence retains its source timestamp and
its stale, unavailable, unconfigured, warning, or critical state. Retrieved text is treated as
untrusted data to reduce prompt-injection risk.

## Use

Start or reconcile the local Compose stack without writing the model key into `.env`:

```powershell
.\scripts\start-ai-station.ps1
```

The wrapper loads the dedicated key from the WSL controller secret store for the lifetime of the
Compose command. It also creates a loopback-only SSH forward on `127.0.0.1:14000` because Docker
Desktop cannot route directly to the LAN on this workstation. The container reaches that local
forward through `host.docker.internal`; LiteLLM remains protected by its scoped virtual key and its
node-side UFW boundary. Ask a question with:

```powershell
.\scripts\ask-ai-lab.ps1 'How is my Kubernetes cluster doing right now?' -Collection homelab
.\scripts\ask-ai-lab.ps1 'What is running in the AI lab?' -Collection ailab
```

The command prints the answer followed by the exact repository line ranges or timestamped runtime
routes used. A missing model gateway produces an explicit service error; invalid or fabricated
model citations are rejected rather than returned to the caller.

The operator wrapper refreshes the runtime snapshots associated with the requested collection
before asking the question. Use `-SkipRefresh` only when deliberately testing stale-data behavior.
The API supplies homelab runtime evidence only for `homelab` requests and Proxmox evidence only for
`ailab` requests, preventing unrelated operational sources from leaking into the answer.

## Open WebUI integration

The same policy is exposed as the OpenAI-compatible `ailab-grounded` model through `/v1/models` and
`/v1/chat/completions`. Open WebUI receives ordinary or SSE-streamed assistant text plus exact
repository line sources. The adapter ignores caller system prompts, automatically scopes explicit
AI lab/homelab/cyberlab questions, and supplies only six bounded prior user/assistant turns for
follow-up resolution. Prior chat is context, never evidence.

## Current boundary

This increment is read-only synthesis. It does not execute remediation, shell commands, arbitrary
queries, or infrastructure changes. Open WebUI now exposes both ordinary raw model chat and this
grounded workflow. Publishing the same policy through authenticated MCP remains the next interface
increment.
