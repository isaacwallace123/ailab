[CmdletBinding()]
param(
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$secretPath = '~/.config/ailab/litellm-keys/orchestrator'
$apiTokenPath = '~/.config/ailab/lab-status-assistant-api-token'
$previousKey = $env:AILAB_LITELLM_API_KEY
$previousApiToken = $env:AILAB_API_TOKEN

try {
    & (Join-Path $PSScriptRoot 'start-gateway-tunnel.ps1')
    $key = (& wsl.exe sh -lc "cat $secretPath").Trim()
    if ($LASTEXITCODE -ne 0 -or $key -notmatch '^sk-[A-Za-z0-9]{40,}$') {
        throw 'The scoped orchestrator key is missing. Reconcile ansible/playbooks/litellm.yml first.'
    }
    $env:AILAB_LITELLM_API_KEY = $key
    $apiToken = (& wsl.exe sh -lc "cat $apiTokenPath").Trim()
    if ($LASTEXITCODE -ne 0 -or $apiToken.Length -lt 40) {
        throw 'The Lab Status Assistant API token is missing from the controller secret store.'
    }
    $env:AILAB_API_TOKEN = $apiToken
    $arguments = @('compose', '--project-directory', $repoRoot, 'up', '-d')
    if (-not $NoBuild) {
        $arguments += '--build'
    }
    & docker @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose failed to start the AI station.'
    }
    & (Join-Path $PSScriptRoot 'start-openwebui-assistant-bridge.ps1')
}
finally {
    $env:AILAB_LITELLM_API_KEY = $previousKey
    $env:AILAB_API_TOKEN = $previousApiToken
    Remove-Variable key -ErrorAction SilentlyContinue
    Remove-Variable apiToken -ErrorAction SilentlyContinue
}
