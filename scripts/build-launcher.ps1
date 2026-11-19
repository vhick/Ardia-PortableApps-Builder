# Windows-only, no external tool installation, UI, or elevation.
# Source: GitHub-hosted windows-2022 image, with VS Enterprise 2022 installed.
# GitHub runner listing: https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('x64', 'arm64')]
  [string]$Architecture
)

$ErrorActionPreference = 'Stop'
$platform = if ($Architecture -eq 'arm64') { 'ARM64' } else { 'x64' }
$hostTarget = if ($Architecture -eq 'arm64') { 'arm64' } else { 'x64' }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$instances = @()
if (Test-Path -LiteralPath $vswhere -PathType Leaf) {
  # Include prerelease and all editions; do not exclude an install by a brittle
  # VS component-ID filter. Verify the exact installed compiler on disk instead.
  $found = @(& $vswhere -all -prerelease -products '*' -version '[17.0,18.0)' -property installationPath)
  if ($LASTEXITCODE -ne 0) { throw "vswhere failed with exit code $LASTEXITCODE" }
  $instances += @($found | Where-Object { $_ -and $_.Trim() })
} else {
  Write-Warning 'vswhere.exe was not found. Checking the documented hosted image path.'
}
$instances += (Join-Path $env:ProgramFiles 'Microsoft Visual Studio/2022/Enterprise')
$instances = @($instances | Select-Object -Unique)

$selected = $null
foreach ($vsPath in $instances) {
  if (-not (Test-Path -LiteralPath $vsPath -PathType Container)) { continue }
  $vcvars = Join-Path $vsPath 'VC/Auxiliary/Build/vcvarsall.bat'
  if (-not (Test-Path -LiteralPath $vcvars -PathType Leaf)) { continue }
  $toolsRoot = Join-Path $vsPath 'VC/Tools/MSVC'
  if (-not (Test-Path -LiteralPath $toolsRoot -PathType Container)) { continue }
  $versions = @(Get-ChildItem -LiteralPath $toolsRoot -Directory -ErrorAction Stop | Sort-Object -Property Name -Descending)
  foreach ($tool in $versions) {
    $cl = Join-Path $tool.FullName "bin/Hostx64/$hostTarget/cl.exe"
    if (Test-Path -LiteralPath $cl -PathType Leaf) {
      $selected = $vsPath
      Write-Host "Found MSVC compiler: $cl"
      break
    }
  }
  if ($selected) { break }
}
if (-not $selected) {
  throw "No functional VS 2022 MSVC Hostx64/$hostTarget compiler found. Searched: $($instances -join '; ')"
}

$cmakeCmd = Get-Command cmake -ErrorAction Stop
$cmakeVersionText = (& cmake --version | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'cmake --version failed' }
$cmakeVersion = ($cmakeVersionText -split '[\r\n]+')[0]
$help = (& cmake --help | Out-String)
if ($LASTEXITCODE -ne 0 -or -not $help.Contains('Visual Studio 17 2022')) {
  throw "Installed CMake at $($cmakeCmd.Source) lacks the Visual Studio 17 2022 generator"
}
Write-Host "MSVC: $selected | CMake: $cmakeVersion | Platform: $platform"
# Explicitly point CMake at the verified installation; no stale generator cache.
cmake -S launcher -B build/launcher -G 'Visual Studio 17 2022' -A $platform "-DCMAKE_GENERATOR_INSTANCE:PATH=$selected"
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed with exit code $LASTEXITCODE" }
cmake --build build/launcher --config Release --parallel 2
if ($LASTEXITCODE -ne 0) { throw "MSVC build failed with exit code $LASTEXITCODE" }
$exe = 'build/launcher/Release/ArdiaPortable.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Build completed without expected launcher at $exe" }
Write-Host "Compiled launcher: $exe"
