param([Parameter(Mandatory)][string]$Identity,[Parameter(Mandatory)][string]$Out)
$ErrorActionPreference='Stop'
$id=Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
if($id.engine_source -cne 'official_setup'){throw 'Setup downloader called for a different engine source'}
$name=[string]$id.asset
$expected="Ardia-$($id.version)-windows-x64-setup.exe"
if($name -cne $expected){throw "Refusing unexpected setup name $name"}
if($id.asset_url -cne "https://github.com/ardia-browser/ardia/releases/download/$($id.tag)/$name"){
 throw 'Setup download URL is not a GitHub release asset from the exact selected source tag'
}
if(([string]$id.asset_sha256) -notmatch '^sha256:[0-9a-fA-F]{64}$'){
 throw 'Refusing setup without a GitHub-published SHA-256 digest'
}
if($id.asset_size -lt 1000000 -or $id.setup_fallback_asset_id -lt 1){throw 'Invalid setup asset metadata'}
New-Item -ItemType Directory -Force -Path $Out | Out-Null
& gh release download $id.tag --repo ardia-browser/ardia --pattern $name --dir $Out --clobber
if($LASTEXITCODE -ne 0){throw "Official same-tag setup download failed: $LASTEXITCODE"}
$path=Join-Path $Out $name
if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Missing downloaded setup: $path"}
if((Get-Item -LiteralPath $path).Length -ne $id.asset_size){throw 'Downloaded setup size does not match official GitHub release asset metadata'}
$sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
if($sha -cne ([string]$id.asset_sha256).Substring(7).ToLowerInvariant()){
 throw "Official setup SHA-256 mismatch: $sha"
}
$id | Add-Member -NotePropertyName downloaded_setup_sha256 -NotePropertyValue $sha -Force
$id | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Identity -Encoding utf8
Write-Host "SHA256-VERIFIED official $($id.tag) Windows setup $name ($sha)"
