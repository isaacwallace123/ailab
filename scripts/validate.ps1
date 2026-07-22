[CmdletBinding()]
param(
    [switch]$SkipContainerConfig
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    uv sync --locked --package lab-status-assistant --extra dev
    uv run --package lab-status-assistant ruff check .
    uv run --package lab-status-assistant ruff format --check .
    uv run --package lab-status-assistant pytest
    uv run --package lab-status-assistant python scripts/validate-cookbook.py
    uv run --package lab-status-assistant python scripts/model-cookbook.py recommend --task lab-ops | Out-Null

    $terraformRoots = @('ai-node-01', 'ai-node-02', 'ai-core-01') | ForEach-Object {
        Join-Path $repoRoot "terraform/environments/$_"
    }
    foreach ($terraformRoot in $terraformRoots) {
        terraform "-chdir=$terraformRoot" fmt -check
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform formatting check failed: $terraformRoot"
        }
        terraform "-chdir=$terraformRoot" init -backend=false -input=false
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform initialization failed: $terraformRoot"
        }
        terraform "-chdir=$terraformRoot" validate
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform validation failed: $terraformRoot"
        }
    }

    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if ($null -ne $wsl) {
        if ($repoRoot -notmatch '^(?<drive>[A-Za-z]):\\(?<path>.+)$') {
            throw "Unable to translate the repository path for WSL validation: $repoRoot"
        }
        $wslDrive = $Matches.drive.ToLowerInvariant()
        $wslPath = $Matches.path -replace '\\', '/'
        $wslRepoRoot = "/mnt/$wslDrive/$wslPath"
        $ansibleCommand = @(
            "cd '$wslRepoRoot/ansible'",
            "export ANSIBLE_CONFIG='$wslRepoRoot/ansible/ansible.cfg'",
            'export AILAB_SSH_PRIVATE_KEY_PATH=/tmp/ailab-syntax-check',
            'ansible-playbook -i inventory/production/hosts.example.yml --syntax-check playbooks/site.yml playbooks/gpu-kernel.yml playbooks/intel-compute.yml playbooks/llama-vulkan.yml playbooks/llama-vulkan-candidate.yml playbooks/litellm.yml playbooks/trust-ai-node-02.yml playbooks/trust-ai-core.yml playbooks/ai-core.yml playbooks/set-ai-core-address.yml playbooks/core-assistant.yml playbooks/migrate-openwebui-state.yml playbooks/retire-ai-node-01-services.yml',
            "bash -n '$wslRepoRoot/scripts/validate-ai-gpu-passthrough.sh' '$wslRepoRoot/scripts/configure-ai-gpu-passthrough.sh'"
        ) -join ' && '
        & wsl.exe sh -lc $ansibleCommand
        if ($LASTEXITCODE -ne 0) {
            throw 'Ansible or host GPU gate validation failed.'
        }
    }

    if (-not $SkipContainerConfig) {
        $docker = Get-Command docker -ErrorAction SilentlyContinue
        if ($null -eq $docker) {
            throw 'Docker CLI is not installed. Use -SkipContainerConfig only for Python-only checks.'
        }
        $previousToken = $env:AILAB_API_TOKEN
        $previousPostgresPassword = $env:AILAB_POSTGRES_PASSWORD
        $previousLiteLLMKey = $env:AILAB_LITELLM_API_KEY
        try {
            $env:AILAB_API_TOKEN = 'compose-validation-only'
            $env:AILAB_POSTGRES_PASSWORD = 'compose-validation-only'
            $env:AILAB_LITELLM_API_KEY = 'compose-validation-only'
            docker compose config --quiet
        }
        finally {
            $env:AILAB_API_TOKEN = $previousToken
            $env:AILAB_POSTGRES_PASSWORD = $previousPostgresPassword
            $env:AILAB_LITELLM_API_KEY = $previousLiteLLMKey
        }
    }
}
finally {
    Pop-Location
}
