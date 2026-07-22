[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('alpaca-api-key-id', 'alpaca-api-secret-key', 'sec-contact-email')]
    [string]$Name
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$writer = Join-Path $repoRoot 'scripts/write-controller-secret.sh'

if ($null -eq (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'WSL is required because AI Lab controller secrets live in the WSL user profile.'
}

$secureValue = Read-Host "Enter $Name" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
try {
    $plainValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if ([string]::IsNullOrWhiteSpace($plainValue)) {
        throw 'Refusing to install an empty value.'
    }
    if ($Name -ne 'sec-contact-email' -and $plainValue.Length -lt 8) {
        throw 'The supplied API credential is implausibly short.'
    }
    if ($Name -eq 'sec-contact-email' -and $plainValue -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') {
        throw 'SEC contact email must be a real deliverable email address.'
    }
    $wslWriter = (& wsl.exe wslpath -a $writer).Trim()
    $plainValue | & wsl.exe bash $wslWriter "finance/$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install finance/$Name."
    }
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    $plainValue = $null
    $secureValue.Dispose()
}

Write-Host "Installed finance/$Name in the private WSL controller store."
Write-Host 'Run scripts/sync-openwebui-workspace.ps1 to apply the finance tool valves.'
