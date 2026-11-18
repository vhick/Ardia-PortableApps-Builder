param([Parameter(Mandatory)][string]$Identity)
$ErrorActionPreference='Stop'
$id=Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
$sha=((& git -C upstream rev-parse HEAD) | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $sha -cne $id.commit){throw "Source SHA mismatch: $sha versus $($id.commit)"}
$tag=((& git -C upstream describe --tags --exact-match HEAD) | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $tag -cne $id.tag){throw "Exact upstream tag mismatch: $tag versus $($id.tag)"}
if(-not(Test-Path -LiteralPath 'upstream\pnpm-lock.yaml')){throw 'No verified dependency lockfile'}
if(-not(Test-Path -LiteralPath 'upstream\scripts\windows\fetch-engine.ps1')){throw 'No upstream verified engine-fetch adapter'}
if(-not(Test-Path -LiteralPath 'upstream\scripts\windows\assemble.ps1')){throw 'No upstream engine-assembly script'}
$lock=(Get-FileHash -LiteralPath 'upstream\pnpm-lock.yaml' -Algorithm SHA256).Hash.ToLowerInvariant()
$id | Add-Member -NotePropertyName lockfile_sha256 -NotePropertyValue $lock -Force
$id | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Identity -Encoding utf8
Write-Host "SOURCE-INSPECTED: tag $tag commit $sha pnpm-lock $lock"
