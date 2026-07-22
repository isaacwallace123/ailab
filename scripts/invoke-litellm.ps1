[CmdletBinding()]
param(
    [ValidateSet('local-auto', 'local-primary', 'local-fast')]
    [string]$Model = 'local-auto',
    [Parameter(Mandatory)]
    [string]$Prompt,
    [string]$GatewayUrl = 'http://192.168.0.221:4000/v1',
    [ValidateSet('personal', 'codex', 'claude', 'gemini', 'cordly', 'open-webui', 'admin')]
    [string]$Identity = 'personal',
    [string]$ControllerKeyPath = ''
)

$ErrorActionPreference = 'Stop'
if (-not $ControllerKeyPath) {
    $ControllerKeyPath = if ($Identity -eq 'admin') {
        '/home/isaac/.config/ailab/litellm-master-key'
    }
    else {
        "/home/isaac/.config/ailab/litellm-keys/$Identity"
    }
}
if ($ControllerKeyPath -notmatch '^/[A-Za-z0-9_./-]+$') {
    throw 'ControllerKeyPath must be a safe absolute WSL path.'
}
$apiKey = (& wsl.exe sh -lc "test -r '$ControllerKeyPath' && tr -d '\r\n' < '$ControllerKeyPath'").Trim()
if ($LASTEXITCODE -ne 0 -or $apiKey.Length -lt 40) {
    throw "The LiteLLM controller key is missing or invalid: $ControllerKeyPath"
}

$headers = @{ Authorization = "Bearer $apiKey" }
$body = @{
    model = $Model
    temperature = 0
    max_tokens = 256
    reasoning_budget = 0
    chat_template_kwargs = @{ enable_thinking = $false }
    messages = @(
        @{ role = 'user'; content = $Prompt }
    )
} | ConvertTo-Json -Depth 8

$response = Invoke-RestMethod `
    -Uri "$($GatewayUrl.TrimEnd('/'))/chat/completions" `
    -Method Post `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $body `
    -TimeoutSec 300

$response.choices[0].message.content
