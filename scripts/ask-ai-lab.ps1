[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateLength(3, 1000)]
    [string]$Question,

    [ValidateSet('ailab', 'homelab', 'cyberlab')]
    [string[]]$Collection,

    [string]$BaseUrl = 'http://127.0.0.1:8088',

    [switch]$SkipRefresh
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$tokenLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -like 'AILAB_API_TOKEN=*' }
if ([string]::IsNullOrWhiteSpace($tokenLine)) {
    throw 'AILAB_API_TOKEN is missing from the ignored .env file.'
}

if (-not $SkipRefresh) {
    $requestedCollections = @($Collection)
    if ($requestedCollections.Count -eq 0 -or 'homelab' -in $requestedCollections) {
        & (Join-Path $PSScriptRoot 'collect-homelab-status.ps1')
        & (Join-Path $PSScriptRoot 'collect-kubernetes-status.ps1')
    }
    if ($requestedCollections.Count -eq 0 -or 'ailab' -in $requestedCollections) {
        & (Join-Path $PSScriptRoot 'collect-proxmox-status.ps1')
    }
}

$body = @{ question = $Question }
if ($Collection.Count -gt 0) {
    $body.collections = $Collection
}
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/api/v1/assistant/ask" `
    -Headers @{ Authorization = "Bearer $($tokenLine.Substring('AILAB_API_TOKEN='.Length))" } `
    -ContentType 'application/json' `
    -Body ($body | ConvertTo-Json) `
    -TimeoutSec 240

$response.answer
''
'Evidence:'
foreach ($citation in $response.citations) {
    if ($null -ne $citation.citation) {
        '  [{0}] {1}:{2}-{3}' -f @(
            $citation.id,
            $citation.source,
            $citation.citation.line_start,
            $citation.citation.line_end
        )
    }
    else {
        '  [{0}] {1} observed {2}' -f @(
            $citation.id,
            $citation.source,
            $citation.observed_at
        )
    }
}
