# Scripts

Local validation and automation helpers.

Cookbook automation:

- `model-cookbook.py` - lists measured/candidate models and recommends routes by hardware fit
- `validate-cookbook.py` - validates cookbook schemas, references, skill metadata, and tool syntax
- `sync-openwebui-workspace.py` - idempotent cookbook-to-Open-WebUI API synchronization
- `sync-openwebui-workspace.ps1` - workstation wrapper that loads the existing WSL controller
  secrets without printing or persisting them
- `test-openwebui-cookbook.ps1` - verifies the live cookbook inventory and native finance-tool call
- `set-ai-provider-key.ps1` - securely installs an optional OpenAI, Anthropic, or Gemini upstream key
- `set-finance-data-secret.ps1` - securely installs Alpaca credentials or the SEC contact identity

Implemented scripts:

- `validate.ps1` — locked dependency sync, lint, formatting, tests, and Compose validation
- `collect-ai-host-facts.sh` — read-only Proxmox storage, capacity, GPU, IOMMU, and network discovery
- `smoke-test.ps1` — live health, authentication, PostgreSQL count, and citation search verification
- `collect-homelab-status.ps1` — host-side fixed-query Prometheus snapshot for Docker Desktop

- `collect-kubernetes-status.ps1` — minimized node, workload, and ArgoCD status snapshot
- `collect-proxmox-status.ps1` — read-only node capacity, storage, and guest inventory snapshot
- `plan-ai-node-01.ps1` — validated, credential-scoped Terraform plan with no apply behavior
- `plan-ai-node-02.ps1` — equivalent plan workflow for the B580 worker
- `invoke-litellm.ps1` — scoped PowerShell client; defaults to the `personal` identity and
  `local-auto`, with explicit identity and alias overrides for integration tests
- `start-ai-station.ps1` — loads the scoped orchestrator key from the WSL controller store and
  starts the Compose knowledge stack without persisting that key in `.env`
- `start-gateway-tunnel.ps1` — maintains the loopback-only Windows SSH forward used by Docker
- `start-openwebui-assistant-bridge.ps1` — legacy-compatible health guard for the core assistant;
  production returns immediately because `ai-core-01` serves the assistant locally
- `test-openwebui-grounded-chat.ps1` — proves model discovery, authoritative roadmap grounding, citations, and follow-up context through Open WebUI
- `set-openwebui-admin-password.ps1` — safely rotates the live Open WebUI admin password and its controller secret together
  Desktop to reach LiteLLM without widening the AI node's UFW rules
- `ask-ai-lab.ps1` — asks the grounded application API a lab question and prints its validated
  repository line ranges or timestamped runtime evidence; refreshes relevant snapshots by default
- `ask-ai-lab.sh` — Git Bash wrapper for `ask-ai-lab.ps1`; forwards the same question and options

The Kubernetes collector minimizes output to status fields and never copies kubeconfig or cluster
credentials into the application container.

`validate-ai-gpu-passthrough.sh` is the read-only host gate for B50/B580 isolation, driver binding,
named PCI mappings, and stopped VM state. Use `--preflight-both` before a binding change and
`--require-both-vfio` after its maintenance reboot.

`configure-ai-gpu-passthrough.sh` is the guarded companion installer. Its default mode is read-only;
`--apply` retains the B50-only policy. `--apply-both` writes the reviewed two-GPU policy and rebuilds
initramfs, while `--rollback` removes only files carrying its ownership marker. It never reboots the
host or starts a VM.

Expected future scripts:

- repo validation
- markdown linting
- service smoke tests
- model endpoint health checks
- dataset manifest checks
- export/sanitize helpers for portfolio demos
