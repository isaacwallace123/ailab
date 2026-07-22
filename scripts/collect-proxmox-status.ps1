[CmdletBinding()]
param(
    [string]$OutputPath = 'artifacts/runtime/cyberlab-proxmox.json'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$resolvedOutput = Join-Path $repoRoot $OutputPath

function Get-DotEnvValue {
    param([string]$Name)

    $line = Get-Content -LiteralPath $envFile |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($line)) {
        throw "$Name is missing from the ignored .env file."
    }
    return $line.Substring($Name.Length + 1)
}

$endpoint = Get-DotEnvValue 'AILAB_PROXMOX_ENDPOINT'
$node = Get-DotEnvValue 'AILAB_PROXMOX_NODE'
$token = Get-DotEnvValue 'AILAB_PROXMOX_API_TOKEN'
$verifyTls = Get-DotEnvValue 'AILAB_PROXMOX_VERIFY_TLS'
$previousToken = $env:AILAB_PROXMOX_API_TOKEN

Push-Location $repoRoot
try {
    $env:AILAB_PROXMOX_API_TOKEN = $token
    $arguments = @(
        'run', '--package', 'lab-status-assistant', 'python', '-m',
        'lab_status_assistant.collect_proxmox_snapshot',
        '--endpoint', $endpoint,
        '--node', $node,
        '--output', $resolvedOutput
    )
    if ($verifyTls.ToLowerInvariant() -notin @('1', 'true', 'yes')) {
        $arguments += '--no-verify-tls'
    }
    & uv @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Proxmox snapshot collection failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:AILAB_PROXMOX_API_TOKEN = $previousToken
    Pop-Location
}
