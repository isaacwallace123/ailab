[CmdletBinding()]
param(
    [string]$PlanPath = 'artifacts/plans/ai-core-01.tfplan'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot '.env'
$terraformRoot = Join-Path $repoRoot 'terraform/environments/ai-core-01'
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

if (-not (Test-Path -LiteralPath $resolvedPlan -PathType Leaf)) {
    throw "Saved Terraform plan does not exist: $resolvedPlan"
}

$previousEndpoint = $env:TF_VAR_proxmox_endpoint
$previousToken = $env:TF_VAR_proxmox_api_token
$previousTls = $env:TF_VAR_proxmox_insecure_tls

try {
    $env:TF_VAR_proxmox_endpoint = Get-DotEnvValue 'AILAB_PROXMOX_ENDPOINT'
    $env:TF_VAR_proxmox_api_token = Get-DotEnvValue 'AILAB_TERRAFORM_PROXMOX_API_TOKEN'
    $env:TF_VAR_proxmox_insecure_tls = ((Get-DotEnvValue 'AILAB_PROXMOX_VERIFY_TLS').ToLowerInvariant() -notin @(
        '1',
        'true',
        'yes'
    )).ToString().ToLowerInvariant()

    terraform "-chdir=$terraformRoot" apply -input=false -auto-approve $resolvedPlan
    if ($LASTEXITCODE -ne 0) { throw 'Terraform apply failed.' }
}
finally {
    $env:TF_VAR_proxmox_endpoint = $previousEndpoint
    $env:TF_VAR_proxmox_api_token = $previousToken
    $env:TF_VAR_proxmox_insecure_tls = $previousTls
}

