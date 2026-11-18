param([Parameter(Mandatory)][string]$Identity)
$ErrorActionPreference='Stop'
$id=Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
$sha=((& git -C upstream rev-parse HEAD) | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $sha -cne $id.commit){throw "Source SHA mismatch: $sha versus $($id.commit)"}
$tag=((& git -C upstream describe --tags --exact-match HEAD) | Out-String).Trim()
if($LASTEXITCODE -ne 0 -or $tag -cne $id.tag){throw "Exact upstream tag mismatch: $tag versus $($id.tag)"}
$paths=@('upstream\pnpm-lock.yaml','upstream\scripts\windows\fetch-engine.ps1','upstream\scripts\windows\assemble.ps1','upstream\scripts\windows\engine\prebuilt.json')
foreach($p in $paths){if(-not(Test-Path -LiteralPath $p)){throw "Required upstream source missing: $p"}}
# Source-level integrity check: preflight examined exactly this immutable manifest.
$manifestPath='upstream\scripts\windows\engine\prebuilt.json'
$manifestHash=(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($manifestHash -cne $id.engine_manifest_sha256){throw "Engine manifest changed after preflight: $manifestHash != $($id.engine_manifest_sha256)"}
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
if($manifest.release -cne $id.engine_release -or $manifest.x64.asset -cne $id.engine_asset -or $manifest.x64.sha256.ToLowerInvariant() -cne $id.engine_sha256){
  throw 'The checked-out source engine identity disagrees with the preflight-approved release/asset/SHA-256'
}
$lock=(Get-FileHash -LiteralPath 'upstream\pnpm-lock.yaml' -Algorithm SHA256).Hash.ToLowerInvariant()
$id | Add-Member -NotePropertyName lockfile_sha256 -NotePropertyValue $lock -Force
$id | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Identity -Encoding utf8
Write-Host "SOURCE-INSPECTED: tag $tag commit $sha pnpm-lock $lock"
Write-Host "PREFLIGHT CROSS-CHECK: $($id.engine_release) / $($id.engine_asset) / $($id.engine_sha256)"
