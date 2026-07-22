[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('openai', 'anthropic', 'gemini')]
    [string]$Provider
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$writer = Join-Path $repoRoot 'scripts/write-controller-secret.sh'
$secretName = "$Provider-api-key"

if ($null -eq (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'WSL is required because AI Lab controller secrets live in the WSL user profile.'
}

$secureValue = Read-Host "Paste the $Provider API key" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
try {
    $plainValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if ([string]::IsNullOrWhiteSpace($plainValue) -or $plainValue.Length -lt 16) {
        throw 'Refusing to install an empty or implausibly short provider key.'
    }
    $wslWriter = (& wsl.exe wslpath -a $writer).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($wslWriter)) {
        throw 'Could not translate the controller secret-writer path for WSL.'
    }
    $plainValue | & wsl.exe bash $wslWriter "providers/$secretName"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the $Provider provider key."
    }
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    $plainValue = $null
    $secureValue.Dispose()
}

Write-Host "Installed the $Provider API key in the private WSL controller store."
Write-Host 'Run the LiteLLM playbook to publish and validate the matching cloud route.'
