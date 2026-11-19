# Verify the ACTUAL MSVC compiler; do not silence setup diagnostics.
# VsDevCmd.bat (official developer prompt) is tried first; vcvars64.bat
# remains an isolated fallback only if environment initialization fails.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$probeRoot = $env:RUNNER_TEMP
if (-not $probeRoot) { $probeRoot = [IO.Path]::GetTempPath() }
$probe = Join-Path $probeRoot 'Ardia MSVC preflight with spaces'
New-Item -ItemType Directory -Path $probe -Force | Out-Null
$source = Join-Path $probe 'ardia msvc preflight.cpp'
$binary = Join-Path $probe 'ardia msvc preflight.exe'
'int main() { return 0; }' | Set-Content -LiteralPath $source -Encoding utf8
$body = @(
    ('cl.exe /nologo /EHsc /Fe:"' + $binary + '" "' + $source + '" /link /SUBSYSTEM:CONSOLE'),
    'if errorlevel 1 (echo Ardia: MSVC compile/link smoke test failed & exit /b 23)',
    ('"' + $binary + '"'),
    'if errorlevel 1 (echo Ardia: MSVC smoke test executable failed & exit /b 24)',
    'exit /b 0'
)
$code = Invoke-ArdiaMsvcTask -BodyLines $body -TaskLabel 'preflight'
if ($code -ne 0) { throw "MSVC preflight failed ($code)" }
if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'MSVC preflight returned success without producing a compiler binary.' }
Write-Host 'WINDOWS-COMPILED: MSVC x64 initialized, C++ fixture compiled, linked, and executed.'
