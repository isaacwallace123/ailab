[CmdletBinding()]
param(
    [string]$Dataset = '/app/datasets/retrieval-eval-v2.yaml',
    [ValidateSet('memory', 'postgres')]
    [string]$Backend = 'postgres'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$previousLiteLLMKey = $env:AILAB_LITELLM_API_KEY

Push-Location $repoRoot
try {
    # Compose validates required interpolation before `exec`, even though the running
    # container already has its scoped key and this command never recreates it.
    $env:AILAB_LITELLM_API_KEY = 'compose-exec-validation-only'
    docker compose exec -T lab-status-assistant `
        python -m lab_status_assistant.evaluation $Dataset --backend $Backend
    if ($LASTEXITCODE -ne 0) {
        throw "Retrieval evaluation failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:AILAB_LITELLM_API_KEY = $previousLiteLLMKey
    Pop-Location
}
