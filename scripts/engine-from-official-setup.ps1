# Controlled source-matched setup fallback: use OFFICIAL same-tag installed binary
# as an engine donor. Upstream ArdiaApp.dll is still compiled from checked-out source.
# The Inno Setup path, if needed, runs only on an ephemeral hosted CI runner.
param([Parameter(Mandatory)][string]$Identity,
      [Parameter(Mandatory)][string]$Setup,
      [Parameter(Mandatory)][string]$CompiledApp,
      [Parameter(Mandatory)][string]$Out)
$ErrorActionPreference='Stop'
$id=Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
if($id.engine_source -cne 'official_setup' -or -not $id.downloaded_setup_sha256){throw 'Unverified official setup strategy'}
if(-not(Test-Path -LiteralPath $Setup -PathType Leaf)){throw 'Official setup missing'}
$actual=(Get-FileHash -LiteralPath $Setup -Algorithm SHA256).Hash.ToLowerInvariant()
if($actual -cne $id.downloaded_setup_sha256){throw 'Downloaded setup changed after verified download'}
if(-not(Test-Path -LiteralPath (Join-Path $CompiledApp 'ArdiaApp.dll') -PathType Leaf)){
 throw 'Source-built ArdiaApp.dll missing'}
if(Test-Path -LiteralPath $Out){throw 'Engine destination must be unused'}
$base=Join-Path $env:RUNNER_TEMP ('ardia-setup-' + $id.commit.Substring(0,10))
if(Test-Path -LiteralPath $base){throw 'Temporary extraction destination already exists; refusing reuse'}
New-Item -ItemType Directory -Force -Path $base | Out-Null
$expanded=Join-Path $base 'extracted'
New-Item -ItemType Directory -Force -Path $expanded | Out-Null
function Get-OfficialPayload([string]$dir){
  $found=@(Get-ChildItem -LiteralPath $dir -Recurse -File -Filter 'Ardia.exe' -ErrorAction Stop | Where-Object {
    $folder=$_.DirectoryName
    (Test-Path -LiteralPath (Join-Path $folder 'ArdiaApp.dll') -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $folder 'chrome.dll') -PathType Leaf)
  })
  if($found.Count -gt 1){throw 'Ambiguous installer contents: multiple app payload roots'}
  if($found.Count -eq 1){return $found[0].DirectoryName}
  return $null
}
# 7-Zip read-only extraction is preferred if the runner can unpack this installer.
$seven=(Get-Command 7z.exe -ErrorAction SilentlyContinue)
if(-not $seven -and (Test-Path 'C:\Program Files\7-Zip\7z.exe')){$seven=Get-Item 'C:\Program Files\7-Zip\7z.exe'}
$payload=$null
if($seven){
  $exe=if($seven.Source){$seven.Source}else{$seven.FullName}
  & $exe x '-y' "-o$expanded" $Setup | Out-Null
  if($LASTEXITCODE -eq 0){$payload=Get-OfficialPayload $expanded}
  if(-not $payload){Write-Host '7-Zip cannot extract the complete Inno Setup payload; trying documented unattended upstream installer switches on ephemeral runner.'}
}
if(-not $payload){
  # Inno Setup officially supports these arguments. No GUI or local user's host is involved.
  # This temporary hosted-runner installation may create transient runner-only shell keys.
  $isolated=Join-Path $base 'isolated-install'
  New-Item -ItemType Directory -Force -Path $isolated | Out-Null
  $log=Join-Path $base 'inno-install.log'
  $args='/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR="' + $isolated + '" /LOG="' + $log + '"'
  $proc=Start-Process -FilePath $Setup -ArgumentList $args -PassThru -WindowStyle Hidden
  if(-not $proc.WaitForExit(240000)){
    try{$proc.Kill()}catch{}
    throw 'Official setup exceeded four-minute noninteractive CI timeout'
  }
  if($proc.ExitCode -ne 0){throw "Official setup could not install into isolated CI folder (exit $($proc.ExitCode)); see Inno log"}
  $payload=Get-OfficialPayload $isolated
  if(-not $payload){throw 'Official Inno Setup produced no verified Ardia.exe / ArdiaApp.dll / chrome.dll trio under isolated install folder'}
}
Write-Host "OFFICIAL PAYLOAD: $payload"
$version=[string]$id.engine_chromium
if($version -notmatch '^\d+\.\d+\.\d+\.\d+$'){throw 'No pinned Chromium version to cross-check'}
$chrome=Join-Path $payload 'chrome.dll'
$reported=([System.Diagnostics.FileVersionInfo]::GetVersionInfo($chrome)).FileVersion
if(-not $reported -or -not $reported.StartsWith($version,[StringComparison]::Ordinal)){
 throw "Official setup Chromium version mismatch: expected $version; chrome.dll reports '$reported'"
}
# Explicitly reject junctions/reparse points, and keep only engine-owned files.
$entries=@(Get-ChildItem -LiteralPath $payload -Recurse -Force)
if($entries | Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0}){
 throw 'Official installer payload contains an unsafe junction/symlink; refusing to package'
}
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$prefix=$payload.TrimEnd('\')+'\'
$sourceFiles=@{}
$srcPrefix=(Resolve-Path -LiteralPath $CompiledApp).Path.TrimEnd('\')+'\'
foreach($item in @(Get-ChildItem -LiteralPath $CompiledApp -Recurse -File)){
 $sourceFiles[$item.FullName.Substring($srcPrefix.Length)]=$true
}
foreach($file in @($entries | Where-Object {-not $_.PSIsContainer})){
 $rel=$file.FullName.Substring($prefix.Length)
 # The source-built app owns these paths; do not import installer duplicate UI files.
 if($rel -ieq 'Ardia.exe' -or $rel -ieq 'ArdiaApp.dll' -or $rel -ieq 'Ardia.ico' -or
    $rel -like 'unins*' -or $rel -like '*.log' -or $rel -like 'Ardia.test-build') {continue}
 if($sourceFiles.ContainsKey($rel)){
   if($rel -ieq 'chrome.dll'){throw 'Source app unexpectedly owns chrome.dll; refusing engine merge'}
   continue
 }
 $target=Join-Path $Out $rel
 New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
 Copy-Item -LiteralPath $file.FullName -Destination $target
}
Copy-Item -LiteralPath (Join-Path $payload 'Ardia.exe') -Destination (Join-Path $Out 'chrome.exe')
if(-not(Test-Path -LiteralPath (Join-Path $Out 'chrome.dll') -PathType Leaf)){
 throw 'Official setup did not yield Chromium chrome.dll'
}
if(Test-Path -LiteralPath (Join-Path $Out 'ArdiaApp.dll')){throw 'Engine directory contains app component; illegal mix'}
Write-Host "ENGINE ASSEMBLY INPUT READY (official same-tag installer, verified Chromium $reported)"
