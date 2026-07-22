# Open WebUI

Open WebUI `0.10.2` runs as `ailab-openwebui.service` on `ai-core-01`. UFW makes the authenticated
UI available to the trusted home LAN:

```text
http://192.168.0.221:8080
```

The UI publishes the raw `local-primary`, `local-fast`, and `local-auto` LiteLLM aliases plus
`ailab-assistant` and `ailab-grounded`. Select `ailab-assistant` for normal use: casual conversation
uses the low-latency local route, lab questions automatically use hybrid RAG, and a message beginning
with `remember that` creates an explicit durable memory. Select `ailab-grounded` when every factual
claim must be constrained to approved evidence. Grounded mode searches the allowlisted AI lab,
homelab, and cyberlab knowledge, conditionally adds read-only runtime evidence, validates
every cited evidence ID, displays repository line sources, and carries bounded context into
follow-up questions. The raw aliases remain useful for ordinary general-purpose model chat.

`ailab-assistant` forwards genuine upstream model chunks, so Open WebUI renders text as it is
generated. `ailab-grounded` intentionally buffers its structured answer until every declared
citation validates; use it when strict validation matters more than immediate token display.

The UI uses separate scoped credentials for LiteLLM and the Lab Status Assistant. It cannot
retrieve either master credential or reach a raw llama.cpp worker. Its persistent application data
uses the isolated `openwebui` database and role on the core's loopback-only PostgreSQL service.

## Workspace Cookbook

The version-controlled [`cookbook/`](../cookbook/README.md) is the source of truth for reusable
Workspace resources. It currently installs these role presets:

| Role | Base route | Main capability boundary |
| :--- | :--- | :--- |
| Personal Assistant | `ailab-assistant` | Everyday chat and per-user explicit personal memory |
| Lab Operator | `local-auto` | Read-only lab knowledge and runtime observation |
| Project Copilot | `local-auto` | Curated projects plus allowlisted GitHub reads |
| Evidence Researcher | `local-auto` | Evidence-led research with Web Search when configured |
| Family Finance Guide | `local-auto` | Education and deterministic calculations, never personalized advice |

These are configuration presets, not fine-tuned model weights. Skills are loaded when relevant,
knowledge is attached by collection ID, and tools are deliberately narrow. Apply reviewed changes
from the workstation with:

Identity is resolved per request from the authenticated Open WebUI account. Cookbook system prompts
use `{{USER_NAME}}`, which Open WebUI replaces with that account's display name. Open WebUI also
forwards the signed-in user ID and display name to the loopback-only Lab Status Assistant. Durable
assistant memories are partitioned by that stable user ID; legacy unscoped memories are archived
under `legacy-unscoped` and are not injected into any current user's conversations. The assistant
must not infer that a user is Isaac, the lab owner, or an administrator merely because they can open
a shared model.

```powershell
.\scripts\sync-openwebui-workspace.ps1 -DryRun
.\scripts\sync-openwebui-workspace.ps1
```

The wrapper reads the existing controller secrets without printing them, updates cookbook-owned
resources in place, and does not delete unrelated Workspace content. The GitHub Reader defaults to
an explicit public-repository allowlist and denies every repository outside it. Re-run the sync
after cookbook changes or a database restore.

## Internet Search and Finance Data

Native Web Search is enabled declaratively through the private SearXNG service, with a maximum of
eight crawled results, bounded loader concurrency, and a per-page content cap. SearXNG and its JSON
API bind only to core loopback; no search port is exposed through UFW. Known loopback and AI-lab
addresses are denied to Open WebUI's URL fetcher to reduce server-side request-forgery exposure.
Web Search is suitable for current news, official policy pages, methodologies, and independent
context; it is not the source of truth for executable prices.

Docling Serve provides local PDF, Office, image, OCR, table, HTML, CSV, and XBRL extraction on an
authenticated loopback-only endpoint. It has no demonstrator UI, remote model services, external
plugins, or custom remote model configurations; uploads are bounded to 50 MiB, 200 pages, one worker,
and a 15-minute document timeout. Docling is an extraction worker, not the general web fetcher.
The controlled research gateway must validate and download each URL, then upload approved bytes to
Docling, so a document URL cannot bypass redirect, destination-address, or content-size policy.

Dad's Finance Guide uses layered evidence:

- Finance Web Research queries the private SearXNG JSON API for stock and finance discovery, then
  opens selected results through the controlled public fetcher or OCR extractor. Search pages and
  snippets are never described as licensed or consolidated real-time quote data.
- SEC EDGAR for issuer filings and structured XBRL facts. Automated SEC calls remain disabled until
  a real operator contact email is installed for the request User-Agent.
- Bank of Canada Valet for keyless official Canadian economic and exchange-rate series.
- Web Search for multiple dated supporting sources and explicit reconciliation of disagreement.

Install an optional SEC contact identity without echoing it, then re-sync the cookbook:

```powershell
.\scripts\set-finance-data-secret.ps1 -Name sec-contact-email
.\scripts\sync-openwebui-workspace.ps1
```

## Cloud Models and Arena

OpenAI, Anthropic Claude, and Google Gemini are optional LiteLLM routes. Provider credentials stay in
the WSL controller store and are never generated or committed. A route is published only when its
real provider key exists. Install keys, deploy the gateway, and Open WebUI will discover the aliases:

```powershell
.\scripts\set-ai-provider-key.ps1 -Provider openai
.\scripts\set-ai-provider-key.ps1 -Provider anthropic
.\scripts\set-ai-provider-key.ps1 -Provider gemini

wsl.exe sh -lc "cd /mnt/c/Users/isaac/Desktop/ailab/ansible && ansible-playbook -i inventory/production/hosts.yml playbooks/litellm.yml"
```

The published aliases are `cloud-openai`, `cloud-claude`, and `cloud-gemini`. Open WebUI's built-in
Arena Model, response rating, and multi-model chats are enabled. Select two models with the `+`
button for an explicit side-by-side comparison, or select Arena Model for blind comparisons and an
Elo-style personal leaderboard. API usage is billed separately by each provider; consumer ChatGPT,
Claude, or Gemini subscriptions are not used by this gateway.

Workspace Tools execute inside Open WebUI and therefore remain a high-trust extension point. This
deployment limits them to deterministic math or calls into read-only authenticated APIs; the
roadmap's isolated MCP service is the preferred shared tool plane for future clients.

## Grounded Assistant Runtime

The Lab Status Assistant and its pgvector database now run in hardened Compose services on
`ai-core-01`. It binds only to core loopback port `18088`; Open WebUI reaches it locally and no
assistant API port is exposed to the LAN. Its copied source allowlist, embedding cache, explicit
memory, and private profile live under `/opt/ailab/core/assistant`. Open WebUI uses two declaratively
managed OpenAI-compatible connections; persistent admin-UI config is disabled so a restart cannot
silently replace the reviewed URLs or scoped keys.

Validate the complete path from the workstation with:

```powershell
.\scripts\test-openwebui-grounded-chat.ps1
```

The acceptance script signs in through Open WebUI itself, requires `ailab-grounded`, checks the
authoritative roadmap answer and source section, then verifies that a follow-up retains the topic while
remaining evidence-grounded.

## Login

The deployment bootstraps one local administrator and disables public signup:

```text
Email: isaac@ailab.local
Password file: /home/isaac/.config/ailab/openwebui-admin-password (WSL controller)
```

Read the password only when logging in:

```powershell
wsl.exe sh -lc "test -r ~/.config/ailab/openwebui-admin-password && cat ~/.config/ailab/openwebui-admin-password"
```

The password, WebUI signing secret, database password, and LiteLLM key are generated once with mode
`0600` and are never committed. The Ansible validation signs in with this managed account, confirms
`local-auto` is visible, and requires public signup to remain disabled.

`WEBUI_ADMIN_EMAIL`, `WEBUI_ADMIN_NAME`, and `WEBUI_ADMIN_PASSWORD` are injected through the
root-only service environment for unattended first boot. Open WebUI uses them only when no users
exist; editing the environment after bootstrap does not rotate an existing account. Rotate the live
password and its controller copy together with:

```powershell
.\scripts\set-openwebui-admin-password.ps1
```

The helper prompts twice without echoing, requires 16–72 UTF-8 bytes, authenticates with the current
controller secret, updates the live account, atomically replaces the mode-`0600` WSL secret, and
verifies the new login. Do not put the plaintext password in `.env`, inventory, or Git.

If the live password changes but the controller write is interrupted, repair only the controller
copy without rotating the account again:

```powershell
.\scripts\set-openwebui-admin-password.ps1 -RepairControllerSecret
```

## Operations

```bash
systemctl status ailab-openwebui.service
curl http://127.0.0.1:8080/ready
journalctl -u ailab-openwebui.service -n 100 --no-pager
```

The service runs as the unprivileged `ailab-webui` user with a hardened systemd sandbox. UFW permits
port 8080 from the trusted `192.168.0.0/24` home LAN. Direct tool-server connections, community sharing, Open WebUI
API-key issuance, Ollama discovery, and OpenAI catch-all passthrough are disabled in the initial
deployment.

Real-time chat requires the browser origin to match `CORS_ALLOW_ORIGIN`. The live acceptance test
performs a Socket.IO WebSocket handshake from the declared `.221` URL before testing model streams,
preventing an address migration from silently degrading chat into refresh-only updates.

Phones and tablets on the same home LAN can open `http://192.168.0.221:8080`. They must be connected
to the primary Wi-Fi rather than an isolated guest/IoT SSID. No AI Lab route is advertised through
Tailscale, and no service is exposed to the public Internet.

Generated HTML and SVG artifacts run in sandboxed iframes with an explicit `IFRAME_CSP`. Inline
scripts and styles, data URLs, and blobs are permitted for self-contained visualizations; outbound
`fetch`, XMLHttpRequest, and WebSocket connections are blocked. Finance visualizations must receive
reviewed numeric data from a tool and must not fetch accounts, market data, or third-party scripts
from inside the rendered artifact.

`ai-core-01` has `onboot=1`, Proxmox deletion protection, enabled native services, and Docker restart
policies. A guest reboot recovered the complete UI, gateway, database, retrieval, and streaming path
without a workstation bridge. The old `.101` Open WebUI and LiteLLM units are stopped, disabled,
masked, and firewalled; their database files remain intact temporarily for rollback.
