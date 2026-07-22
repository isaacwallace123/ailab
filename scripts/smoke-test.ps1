[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8088'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'

if (-not (Test-Path -LiteralPath $envFile)) {
    throw 'The ignored .env file is required for the authenticated smoke test.'
}

$tokenLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -like 'AILAB_API_TOKEN=*' }
if ([string]::IsNullOrWhiteSpace($tokenLine)) {
    throw 'AILAB_API_TOKEN is missing from .env.'
}

$token = $tokenLine.Substring('AILAB_API_TOKEN='.Length)
$headers = @{ Authorization = "Bearer $token" }

function Wait-ServiceReady {
    param([string]$Uri)

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            return Invoke-RestMethod -Uri $Uri -TimeoutSec 3
        }
        catch {
            if ($attempt -eq 30) {
                throw "Service did not become ready within 30 attempts: $Uri"
            }
            Start-Sleep -Seconds 1
        }
    }
}

& (Join-Path $PSScriptRoot 'collect-homelab-status.ps1')
& (Join-Path $PSScriptRoot 'collect-kubernetes-status.ps1')
& (Join-Path $PSScriptRoot 'collect-proxmox-status.ps1')

$live = Wait-ServiceReady -Uri "$BaseUrl/health/live"
$ready = Wait-ServiceReady -Uri "$BaseUrl/health/ready"

try {
    Invoke-WebRequest -Uri "$BaseUrl/api/v1/collections" -UseBasicParsing | Out-Null
    throw 'Unauthenticated API request unexpectedly succeeded.'
}
catch {
    if ([int]$_.Exception.Response.StatusCode -ne 401) {
        throw
    }
}

$body = @{
    query       = 'ArgoCD Kubernetes health'
    collections = @('homelab')
    limit       = 3
} | ConvertTo-Json

$search = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/api/v1/knowledge/search" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $body

$runtime = Invoke-RestMethod -Uri "$BaseUrl/api/v1/status/runtime/homelab" -Headers $headers
$kubernetes = Invoke-RestMethod `
    -Uri "$BaseUrl/api/v1/status/runtime/homelab/kubernetes" `
    -Headers $headers
$proxmox = Invoke-RestMethod `
    -Uri "$BaseUrl/api/v1/status/runtime/ailab/proxmox" `
    -Headers $headers

$assistantBody = @{
    question    = 'How is the Kubernetes cluster doing right now?'
    collections = @('homelab')
} | ConvertTo-Json
$assistant = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/api/v1/assistant/ask" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $assistantBody `
    -TimeoutSec 240

if ($search.results.Count -lt 1) {
    throw 'Authenticated search returned no results.'
}

if ($runtime.state -in @('unavailable', 'unconfigured')) {
    throw "Homelab runtime connector state is $($runtime.state)."
}

if ($kubernetes.state -in @('unavailable', 'unconfigured')) {
    throw "Kubernetes runtime connector state is $($kubernetes.state)."
}

if ($proxmox.state -in @('unavailable', 'unconfigured')) {
    throw "Proxmox runtime connector state is $($proxmox.state)."
}

if ($assistant.citations.Count -lt 1 -or $assistant.answer -notmatch '\[[KR]\d+\]') {
    throw 'Grounded assistant returned an answer without validated evidence citations.'
}

$databaseCount = docker exec -i ailab-postgres-1 `
    psql -U ailab -d ailab -Atc 'SELECT count(*) FROM knowledge_chunks;'

if ([int]$databaseCount -ne [int]$ready.chunks) {
    throw "API chunk count $($ready.chunks) does not match PostgreSQL count $databaseCount."
}

[pscustomobject]@{
    Live          = $live.status
    Ready         = $ready.status
    SearchBackend = $ready.search_backend
    Documents     = $ready.documents
    Chunks        = $ready.chunks
    SearchResults = $search.results.Count
    HomelabState  = $runtime.state
    ActiveAlerts  = @($runtime.alerts | Where-Object state -eq 'firing').Count
    KubernetesState = $kubernetes.state
    ReadyNodes      = ($kubernetes.signals | Where-Object name -eq 'ready_nodes').value
    HealthyArgoApps = ($kubernetes.signals | Where-Object name -eq 'healthy_argocd_applications').value
    KubernetesIssues = @($kubernetes.issues).Count
    ProxmoxState      = $proxmox.state
    ProxmoxStorages   = @($proxmox.storages | Where-Object active).Count
    ProxmoxGuests     = @($proxmox.guests).Count
    AssistantModel    = $assistant.model
    AssistantCitations = $assistant.citations.Count
}
