[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://192.168.0.221:8080',
    [string]$Email = 'isaac@ailab.local',
    [switch]$RepairControllerSecret
)

$ErrorActionPreference = 'Stop'
$secretPath = '~/.config/ailab/openwebui-admin-password'
$repoRoot = Split-Path -Parent $PSScriptRoot

function ConvertFrom-LocalSecureString {
    param([Security.SecureString]$SecureValue)

    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Install-ControllerSecret {
    param([string]$Value)

    if ($repoRoot -notmatch '^(?<drive>[A-Za-z]):\\(?<path>.+)$') {
        throw "Unable to translate the repository path for WSL: $repoRoot"
    }
    $wslDrive = $Matches.drive.ToLowerInvariant()
    $wslPath = $Matches.path -replace '\\', '/'
    $helperPath = "/mnt/$wslDrive/$wslPath/scripts/write-controller-secret.sh"
    $Value | wsl.exe bash $helperPath openwebui-admin-password
    if ($LASTEXITCODE -ne 0) {
        throw 'The controller secret could not be updated.'
    }
}

function Test-OpenWebUILogin {
    param([string]$Password)

    $body = @{
        email = $Email
        password = $Password
    } | ConvertTo-Json
    return Invoke-RestMethod `
        -Method Post `
        -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/auths/signin" `
        -ContentType 'application/json' `
        -Body $body `
        -TimeoutSec 20
}

if ($RepairControllerSecret) {
    $liveSecurePassword = Read-Host 'Current live Open WebUI admin password' -AsSecureString
    $livePassword = ConvertFrom-LocalSecureString $liveSecurePassword
    try {
        $null = Test-OpenWebUILogin $livePassword
        Install-ControllerSecret $livePassword
        Write-Host 'The controller secret now matches the live Open WebUI password.'
        return
    }
    finally {
        $livePassword = $null
    }
}

$currentPassword = (& wsl.exe sh -lc "cat $secretPath").Trim()
if ($LASTEXITCODE -ne 0 -or $currentPassword.Length -lt 16) {
    throw 'The current Open WebUI administrator password is unavailable.'
}

$newSecurePassword = Read-Host 'New Open WebUI admin password' -AsSecureString
$confirmSecurePassword = Read-Host 'Confirm the new password' -AsSecureString
$newPassword = ConvertFrom-LocalSecureString $newSecurePassword
$confirmation = ConvertFrom-LocalSecureString $confirmSecurePassword
try {
    if (-not [string]::Equals($newPassword, $confirmation, [StringComparison]::Ordinal)) {
        throw 'The new passwords do not match.'
    }
    $passwordBytes = [Text.Encoding]::UTF8.GetByteCount($newPassword)
    if ($passwordBytes -lt 12 -or $passwordBytes -gt 72) {
        throw 'Use a password between 12 and 72 UTF-8 bytes.'
    }
    if ([string]::Equals($currentPassword, $newPassword, [StringComparison]::Ordinal)) {
        throw 'The new password must differ from the current password.'
    }

    $signin = Test-OpenWebUILogin $currentPassword

    $updateBody = @{
        password = $currentPassword
        new_password = $newPassword
    } | ConvertTo-Json
    $updated = Invoke-RestMethod `
        -Method Post `
        -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/auths/update/password" `
        -Headers @{ Authorization = "Bearer $($signin.token)" } `
        -ContentType 'application/json' `
        -Body $updateBody `
        -TimeoutSec 20
    if ($updated -ne $true) {
        throw 'Open WebUI did not confirm the password update.'
    }

    try {
        Install-ControllerSecret $newPassword
    }
    catch {
        throw 'The account changed, but the controller secret could not be updated. Run this script with -RepairControllerSecret.'
    }

    $null = Test-OpenWebUILogin $newPassword

    Write-Host 'Open WebUI administrator password and controller secret updated successfully.'
}
finally {
    $currentPassword = $null
    $newPassword = $null
    $confirmation = $null
    $signin = $null
    $updateBody = $null
}
