[CmdletBinding()]
param(
    [string]$PlanPath = 'artifacts/plans/ai-node-01.tfplan'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$terraformRoot = Join-Path $repoRoot 'terraform/environments/ai-node-01'
$resolvedPlan = Join-Path $repoRoot $PlanPath

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
$apiToken = Get-DotEnvValue 'AILAB_TERRAFORM_PROXMOX_API_TOKEN'
$insecureTls = (Get-DotEnvValue 'AILAB_PROXMOX_VERIFY_TLS').ToLowerInvariant() -notin @(
    '1',
    'true',
    'yes'
)
$publicKeyPath = Get-DotEnvValue 'AILAB_SSH_PUBLIC_KEY_PATH'
if (-not (Test-Path -LiteralPath $publicKeyPath -PathType Leaf)) {
    throw "SSH public key does not exist: $publicKeyPath"
}
$publicKey = (Get-Content -LiteralPath $publicKeyPath -Raw).Trim()

$previousEndpoint = $env:TF_VAR_proxmox_endpoint
$previousToken = $env:TF_VAR_proxmox_api_token
$previousTls = $env:TF_VAR_proxmox_insecure_tls
$previousKeys = $env:TF_VAR_ssh_public_keys

try {
    $env:TF_VAR_proxmox_endpoint = $endpoint
    $env:TF_VAR_proxmox_api_token = $apiToken
    $env:TF_VAR_proxmox_insecure_tls = $insecureTls.ToString().ToLowerInvariant()
    # -InputObject preserves a single-key array; pipeline input is enumerated and
    # ConvertTo-Json would otherwise serialize one key as a scalar string.
    $env:TF_VAR_ssh_public_keys = ConvertTo-Json -InputObject @($publicKey) -Compress

    New-Item -ItemType Directory -Path (Split-Path -Parent $resolvedPlan) -Force | Out-Null
    terraform "-chdir=$terraformRoot" init -backend=false -input=false
    if ($LASTEXITCODE -ne 0) {
        throw 'Terraform initialization failed.'
    }
    terraform "-chdir=$terraformRoot" validate
    if ($LASTEXITCODE -ne 0) {
        throw 'Terraform validation failed.'
    }
    terraform "-chdir=$terraformRoot" plan -input=false "-out=$resolvedPlan"
    if ($LASTEXITCODE -ne 0) {
        throw 'Terraform plan failed.'
    }
}
finally {
    $env:TF_VAR_proxmox_endpoint = $previousEndpoint
    $env:TF_VAR_proxmox_api_token = $previousToken
    $env:TF_VAR_proxmox_insecure_tls = $previousTls
    $env:TF_VAR_ssh_public_keys = $previousKeys
}
