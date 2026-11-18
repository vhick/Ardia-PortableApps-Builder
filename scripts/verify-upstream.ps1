param([Parameter(Mandatory)][string]$Identity)
$ErrorActionPreference = 'Stop'
$id = Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
$sha = ((& git -C upstream rev-parse HEAD) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $sha -cne $id.commit) { throw "Source SHA mismatch: $sha versus $($id.commit)" }
$tag = ((& git -C upstream describe --tags --exact-match HEAD) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $tag -cne $id.tag) { throw "Exact upstream tag mismatch: $tag versus $($id.tag)" }
$paths = @('upstream\pnpm-lock.yaml', 'upstream\scripts\windows\fetch-engine.ps1', 'upstream\scripts\windows\assemble.ps1', 'upstream\scripts\windows\engine\prebuilt.json')
foreach ($p in $paths) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Required upstream source missing: $p" }
}
# GitHub API preflight hashes the exact Git blob. Git for Windows can use CRLF in
# the worktree. A local file hash is therefore not an authoritative blob hash.
# Python reads Git blob *bytes*, compares them against preflight SHA-256 and
# validates the checked-out file differs by line endings only.
& python scripts/verify-source-content.py --identity $Identity --repo upstream
if ($LASTEXITCODE -ne 0) { throw "Immutable upstream source integrity verification failed (exit code $LASTEXITCODE)" }
$id = Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
Write-Host "SOURCE-INSPECTED: tag $tag commit $sha pnpm-lock $($id.lockfile_sha256)"
