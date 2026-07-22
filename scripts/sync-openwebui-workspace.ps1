[CmdletBinding()]
param(
    [string]$Url = 'http://192.168.0.221:8080',
    [string]$Email = 'isaac@ailab.local',
    [string]$GitHubRepositories = 'isaacwallace123/homelab-k8s,isaacwallace123/portbuildr,isaacwallace123/BotProject,isaacwallace123/hypepot',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    if ($DryRun) {
        uv run --package lab-status-assistant python scripts/sync-openwebui-workspace.py --url $Url --email $Email --dry-run
        if ($LASTEXITCODE -ne 0) {
            throw 'Open WebUI cookbook dry run failed.'
        }
        return
    }

    if ($null -eq (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw 'WSL is required to read the existing AI Lab controller secrets.'
    }

    $adminPassword = (& wsl.exe sh -lc 'test -r ~/.config/ailab/openwebui-admin-password && cat ~/.config/ailab/openwebui-admin-password').Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($adminPassword)) {
        throw 'The Open WebUI controller password is missing or unreadable.'
    }
    $assistantToken = (& wsl.exe sh -lc 'test -r ~/.config/ailab/lab-status-assistant-api-token && cat ~/.config/ailab/lab-status-assistant-api-token').Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($assistantToken)) {
        throw 'The Lab Status Assistant controller token is missing or unreadable.'
    }
    $researchGatewayKey = (& wsl.exe sh -lc 'test -r ~/.config/ailab/research-gateway-api-key && cat ~/.config/ailab/research-gateway-api-key').Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($researchGatewayKey)) {
        throw 'The Research Gateway controller key is missing or unreadable.'
    }
    $alpacaKeyId = (@(& wsl.exe sh -lc 'test -r ~/.config/ailab/finance/alpaca-api-key-id && cat ~/.config/ailab/finance/alpaca-api-key-id || true') -join '').Trim()
    $alpacaSecret = (@(& wsl.exe sh -lc 'test -r ~/.config/ailab/finance/alpaca-api-secret-key && cat ~/.config/ailab/finance/alpaca-api-secret-key || true') -join '').Trim()
    $secContactEmail = (@(& wsl.exe sh -lc 'test -r ~/.config/ailab/finance/sec-contact-email && cat ~/.config/ailab/finance/sec-contact-email || true') -join '').Trim()

    $previousPassword = $env:OPENWEBUI_PASSWORD
    $previousAssistantToken = $env:AILAB_API_TOKEN
    $previousResearchGatewayKey = $env:RESEARCH_GATEWAY_API_KEY
    $previousRepositories = $env:AILAB_GITHUB_REPOSITORIES
    $previousAlpacaKeyId = $env:ALPACA_API_KEY_ID
    $previousAlpacaSecret = $env:ALPACA_API_SECRET_KEY
    $previousSecContact = $env:SEC_CONTACT_EMAIL
    try {
        $env:OPENWEBUI_PASSWORD = $adminPassword
        $env:AILAB_API_TOKEN = $assistantToken
        $env:RESEARCH_GATEWAY_API_KEY = $researchGatewayKey
        $env:AILAB_GITHUB_REPOSITORIES = $GitHubRepositories
        $env:ALPACA_API_KEY_ID = $alpacaKeyId
        $env:ALPACA_API_SECRET_KEY = $alpacaSecret
        $env:SEC_CONTACT_EMAIL = $secContactEmail
        uv run --package lab-status-assistant python scripts/sync-openwebui-workspace.py --url $Url --email $Email
        if ($LASTEXITCODE -ne 0) {
            throw 'Open WebUI cookbook sync failed.'
        }
    }
    finally {
        $env:OPENWEBUI_PASSWORD = $previousPassword
        $env:AILAB_API_TOKEN = $previousAssistantToken
        $env:RESEARCH_GATEWAY_API_KEY = $previousResearchGatewayKey
        $env:AILAB_GITHUB_REPOSITORIES = $previousRepositories
        $env:ALPACA_API_KEY_ID = $previousAlpacaKeyId
        $env:ALPACA_API_SECRET_KEY = $previousAlpacaSecret
        $env:SEC_CONTACT_EMAIL = $previousSecContact
        $adminPassword = $null
        $assistantToken = $null
        $researchGatewayKey = $null
        $alpacaKeyId = $null
        $alpacaSecret = $null
    }
}
finally {
    Pop-Location
}
