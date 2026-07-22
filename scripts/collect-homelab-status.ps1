[CmdletBinding()]
param(
    [string]$PrometheusUrl = 'http://192.168.0.241',
    [string]$OutputPath = 'artifacts/runtime/homelab-prometheus.json'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = Join-Path $repoRoot $OutputPath

Push-Location $repoRoot
try {
    uv run --package lab-status-assistant python -m `
        lab_status_assistant.collect_prometheus_snapshot `
        --url $PrometheusUrl `
        --output $resolvedOutput
}
finally {
    Pop-Location
}

