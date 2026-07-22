[CmdletBinding()]
param(
    [string]$OutputPath = 'artifacts/runtime/homelab-kubernetes.json',
    [string]$Context = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = Join-Path $repoRoot $OutputPath

Push-Location $repoRoot
try {
    $arguments = @(
        'run', '--package', 'lab-status-assistant', 'python', '-m',
        'lab_status_assistant.collect_kubernetes_snapshot',
        '--output', $resolvedOutput
    )
    if (-not [string]::IsNullOrWhiteSpace($Context)) {
        $arguments += @('--context', $Context)
    }
    & uv @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Kubernetes snapshot collection failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
