[CmdletBinding()]
param(
    [int]$RemotePort = 18088,
    [int]$LocalPort = 8088,
    [string]$Destination = 'isaac@192.168.0.221',
    [string]$HostKeyAlias = 'ai-core-01'
)

$ErrorActionPreference = 'Stop'
$sshPath = Join-Path $env:SystemRoot 'System32\OpenSSH\ssh.exe'
$identityPath = Join-Path $env:USERPROFILE '.ssh\id_ed25519'
$commonArguments = @(
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    '-o', "HostKeyAlias=$HostKeyAlias",
    '-o', 'StrictHostKeyChecking=yes',
    '-i', $identityPath
)

$localReady = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $localHealth = Invoke-WebRequest `
            -Uri "http://127.0.0.1:$LocalPort/health/ready" `
            -UseBasicParsing `
            -TimeoutSec 5
        if ($localHealth.StatusCode -eq 200) {
            $localReady = $true
            break
        }
    }
    catch {
        if ($attempt -eq 30) {
            throw 'The local Lab Status Assistant did not become ready within 60 seconds.'
        }
    }
    Start-Sleep -Seconds 2
}
if (-not $localReady) {
    throw 'The local Lab Status Assistant is not ready.'
}

& $sshPath @commonArguments $Destination `
    "curl -fs --max-time 5 http://127.0.0.1:$RemotePort/health/ready >/dev/null" 2>$null
if ($LASTEXITCODE -eq 0) {
    return
}

$tunnelArguments = @(
    '-N',
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    '-o', "HostKeyAlias=$HostKeyAlias",
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-i', $identityPath,
    '-R', "127.0.0.1:${RemotePort}:127.0.0.1:${LocalPort}",
    $Destination
)
$process = Start-Process `
    -FilePath $sshPath `
    -ArgumentList $tunnelArguments `
    -WindowStyle Hidden `
    -PassThru
Start-Sleep -Seconds 2
if ($process.HasExited) {
    throw "The Open WebUI assistant bridge exited with code $($process.ExitCode)."
}

& $sshPath @commonArguments $Destination `
    "curl -fs --max-time 5 http://127.0.0.1:$RemotePort/health/ready >/dev/null"
if ($LASTEXITCODE -ne 0) {
    Stop-Process -Id $process.Id
    throw 'The Open WebUI assistant bridge failed its health check.'
}
