[CmdletBinding()]
param(
    [string]$AssistantContainer = 'ailab-lab-status-assistant-1',
    [string]$DatabaseContainer = 'ailab-postgres-1'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$artifactRoot = Join-Path $repoRoot 'artifacts/core-assistant'
$homelabRoot = Join-Path (Split-Path -Parent $repoRoot) 'homelab'
$cyberlabRoot = Join-Path (Split-Path -Parent $repoRoot) 'cyberlab'

foreach ($path in @($repoRoot, $homelabRoot, $cyberlabRoot)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Required repository directory does not exist: $path"
    }
}
New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

$runningContainers = @(docker ps --format '{{.Names}}')
if ($DatabaseContainer -notin $runningContainers -or $AssistantContainer -notin $runningContainers) {
    throw 'The workstation assistant and PostgreSQL containers must be running to package live state.'
}

docker exec $DatabaseContainer pg_dump -U ailab -d ailab -Fc -f /tmp/ailab-core-migration.dump
if ($LASTEXITCODE -ne 0) { throw 'The assistant database dump failed.' }
try {
    docker cp "${DatabaseContainer}:/tmp/ailab-core-migration.dump" (Join-Path $artifactRoot 'ailab.dump')
    if ($LASTEXITCODE -ne 0) { throw 'Copying the assistant database dump failed.' }
}
finally {
    docker exec $DatabaseContainer rm -f /tmp/ailab-core-migration.dump | Out-Null
}

$embeddingArchiveName = '.ailab-embeddings-export.tar.gz'
$embeddingArchiveContainer = "/models/embeddings/$embeddingArchiveName"
$embeddingArchiveHost = Join-Path $repoRoot "models/cache/embeddings/$embeddingArchiveName"
docker exec $AssistantContainer tar --ignore-failed-read --warning=no-file-changed `
    --exclude="embeddings/$embeddingArchiveName" `
    -czf $embeddingArchiveContainer -C /models embeddings
if ($LASTEXITCODE -ne 0) { throw 'Packaging the embedding cache failed.' }
try {
    Move-Item -LiteralPath $embeddingArchiveHost `
        -Destination (Join-Path $artifactRoot 'embeddings.tar.gz') -Force
}
finally {
    Remove-Item -LiteralPath $embeddingArchiveHost -Force -ErrorAction SilentlyContinue
}

function Invoke-Tar {
    param([string[]]$Arguments)

    & tar.exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "tar.exe failed: $($Arguments -join ' ')"
    }
}

Invoke-Tar @('-czf', (Join-Path $artifactRoot 'app.tar.gz'), '-C',
    (Join-Path $repoRoot 'services/lab-status-assistant'), '.')
Invoke-Tar @('-czf', (Join-Path $artifactRoot 'ailab-sources.tar.gz'),
    '--exclude=models/cache', '--exclude=artifacts', '--exclude=.private', '--exclude=.env',
    '-C', $repoRoot, 'README.md', 'HANDOFF.md', 'docs', 'services', 'models', 'datasets')
Invoke-Tar @('-czf', (Join-Path $artifactRoot 'homelab-sources.tar.gz'),
    '--exclude=.git', '--exclude=.env', '--exclude=*secret*', '-C', $homelabRoot,
    'README.md', 'docs', 'argocd-apps', 'manifests')
Invoke-Tar @('-czf', (Join-Path $artifactRoot 'cyberlab-sources.tar.gz'),
    '--exclude=.git', '--exclude=.terraform', '--exclude=*.tfstate*', '--exclude=*.tfvars*',
    '--exclude=.env', '--exclude=*secret*', '-C', $cyberlabRoot,
    'README.md', 'docs', 'schemas', 'scenarios', 'terraform')
Invoke-Tar @('-czf', (Join-Path $artifactRoot 'runtime.tar.gz'), '-C',
    (Join-Path $repoRoot 'artifacts'), 'runtime')

Get-ChildItem -LiteralPath $artifactRoot -File |
    Sort-Object Name |
    Select-Object Name, Length
