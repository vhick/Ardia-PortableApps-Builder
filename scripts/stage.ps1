param([Parameter(Mandatory)][string]$App,[Parameter(Mandatory)][string]$Stage,[Parameter(Mandatory)][string]$Identity)
$ErrorActionPreference='Stop'
$id=Get-Content -LiteralPath $Identity -Raw -Encoding utf8 | ConvertFrom-Json
if(-not(Test-Path -LiteralPath (Join-Path $App 'Ardia.exe')) -or -not(Test-Path -LiteralPath (Join-Path $App 'ArdiaApp.dll')) -or -not(Test-Path -LiteralPath (Join-Path $App 'chrome.dll'))) {throw 'Upstream app was not fully assembled'}
$root=Join-Path $Stage 'ArdiaPortable'
if(Test-Path -LiteralPath $root){throw 'Refusing to reuse an existing staging directory'}
New-Item -ItemType Directory -Force -Path (Join-Path $root 'App\Ardia'),(Join-Path $root 'App\AppInfo'),(Join-Path $root 'Data\Ardia'),(Join-Path $root 'Other\Source') | Out-Null
# Copy all assembled files, including resources and subdirectories.
Get-ChildItem -LiteralPath $App -Force | Copy-Item -Destination (Join-Path $root 'App\Ardia') -Recurse -Force
if(Get-ChildItem -LiteralPath (Join-Path $root 'App\Ardia') -Recurse -File -Filter 'Ardia.test-build' | Select-Object -First 1){throw 'Never ship Ardia.test-build'}
$icon=Join-Path $env:GITHUB_WORKSPACE 'upstream\apps\browser\windows\Ardia\Ardia.ico'
if(-not(Test-Path -LiteralPath $icon)){throw 'Upstream icon missing: do not invent one'}
Copy-Item -LiteralPath $icon -Destination (Join-Path $root 'App\AppInfo\appicon.ico')
Copy-Item -LiteralPath $icon -Destination (Join-Path $root 'App\Ardia\Ardia.ico')
Add-Type -AssemblyName System.Drawing
foreach($size in @(16,32)){
  $img=[System.Drawing.Icon]::new($icon,$size,$size)
  try{$bitmap=$img.ToBitmap();try{$bitmap.Save((Join-Path $root "App\AppInfo\appicon_$size.png"),[System.Drawing.Imaging.ImageFormat]::Png)}finally{$bitmap.Dispose()}}finally{$img.Dispose()}
}
$ini=@"
[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=Ardia Portable (Unofficial)
AppID=ArdiaBrowserPortableVhick
Publisher=Ardia contributors and unofficial portable packagers
Homepage=https://github.com/ardia-browser/ardia
Category=Internet
Description=Chromium-based browser with portable profile redirection
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true
EULAVersion=1

[Version]
PackageVersion=$($id.package_version)
DisplayVersion=$($id.version) Unofficial b1r3

[Control]
Icons=1
Start=ArdiaPortable.exe
"@
[System.IO.File]::WriteAllText((Join-Path $root 'App\AppInfo\appinfo.ini'),$ini,[Text.UTF8Encoding]::new($false))
foreach($f in @('LICENSE','LICENSE.Apache-2.0','NOTICE')){
  $src=Join-Path $env:GITHUB_WORKSPACE "upstream\$f"
  if(-not(Test-Path -LiteralPath $src)){throw "Required upstream attribution missing: $f"}
  Copy-Item -LiteralPath $src -Destination (Join-Path $root "Other\Source\$f")
}
$source="Ardia source: https://github.com/ardia-browser/ardia/tree/$($id.tag)`nUpstream commit: $($id.commit)`nBuild: source-built Windows x64 app plus official checksum-verified prebuilt engine via upstream scripts/windows/fetch-engine.ps1`nThe source and engine GPL/Apache/Chromium/uBlock notices are in NOTICE and upstream source; see release assets for source.`n"
[IO.File]::WriteAllText((Join-Path $root 'Other\Source\SOURCE.txt'),$source,[Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'launcher\ArdiaPortable.cpp') -Destination (Join-Path $root 'Other\Source\ArdiaPortable.cpp')
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'launcher\ArdiaLaunchFlags.h') -Destination (Join-Path $root 'Other\Source\ArdiaLaunchFlags.h')
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'LICENSE.builder') -Destination (Join-Path $root 'Other\Source\LICENSE.builder')
Copy-Item -LiteralPath (Join-Path $env:GITHUB_WORKSPACE 'upstream\scripts\windows\engine\prebuilt.json') -Destination (Join-Path $root 'Other\Source\engine-prebuilt.json')
Copy-Item -LiteralPath $Identity -Destination (Join-Path $root 'Other\Source\build-identity.json')
Write-Host "Staged $root"
