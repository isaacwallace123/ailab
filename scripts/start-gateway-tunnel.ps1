[CmdletBinding()]
param(
    [string]$ListenAddress = '127.0.0.1',
    [int]$ListenPort = 14000
)

$ErrorActionPreference = 'Stop'
$existing = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    $health = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$ListenPort/health/liveliness" `
        -UseBasicParsing `
        -TimeoutSec 5
    if ($health.StatusCode -eq 200) {
        return
    }
    throw "Port $ListenPort is already used by a different service."
}

$sshPath = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
$identityPath = Join-Path $env:USERPROFILE '.ssh\id_ed25519'
$arguments = @(
    '-N',
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    '-o', 'HostKeyAlias=ai-core-01',
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-i', $identityPath,
    '-L', "${ListenAddress}:${ListenPort}:127.0.0.1:4000",
    'isaac@192.168.0.221'
)
$process = Start-Process `
    -FilePath $sshPath `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -PassThru
Start-Sleep -Seconds 2
if ($process.HasExited) {
    throw "The AI gateway SSH tunnel exited with code $($process.ExitCode)."
}

$health = Invoke-WebRequest `
    -Uri "http://127.0.0.1:$ListenPort/health/liveliness" `
    -UseBasicParsing `
    -TimeoutSec 5
if ($health.StatusCode -ne 200) {
    Stop-Process -Id $process.Id
    throw 'The AI gateway SSH tunnel failed its health check.'
}
