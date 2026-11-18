param([Parameter(Mandatory)][ValidateSet('before','after')][string]$Phase,
      [string]$Folder='portable-host-audit')
# Read-only observation; run BEFORE and AFTER a manual browser session.
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $Folder|Out-Null
$target=Join-Path $Folder "$Phase.json"
$paths=@(
  (Join-Path $env:LOCALAPPDATA 'Ardia'),
  (Join-Path $env:APPDATA 'Ardia'),
  (Join-Path $env:LOCALAPPDATA 'Programs\Ardia')
)
$entries=@()
foreach($path in $paths){
  if(-not(Test-Path -LiteralPath $path)){continue}
  foreach($file in @(Get-ChildItem -LiteralPath $path -Force -Recurse -File -ErrorAction SilentlyContinue)){
    if(($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){continue}
    $entries+=@{path=$file.FullName;size=$file.Length;modified=$file.LastWriteTimeUtc.ToString('o')}
  }
}
$reg=@()
foreach($key in @('HKCU:\Software\Classes\ArdiaHTM','HKCU:\Software\Clients\StartMenuInternet\Ardia', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run')){
  if(Test-Path $key){$reg+=@{key=$key;present=$true}}
}
[pscustomobject]@{phase=$Phase;when=(Get-Date).ToUniversalTime().ToString('o');files=$entries;registry=$reg}|
  ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $target -Encoding utf8
Write-Host "Read-only $Phase snapshot: $target. Do not automatically delete any reported host files."
