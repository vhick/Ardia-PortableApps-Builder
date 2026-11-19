param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Launcher source absent: $Source" }
$dir = Split-Path -Parent $Output
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$body = @(
    ('cl.exe /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE /MT /Fe:"' + $Output + '" "' + $Source + '" /link /SUBSYSTEM:WINDOWS shell32.lib'),
    'if errorlevel 1 (echo Ardia: launcher compile/link failed & exit /b 23)',
    'exit /b 0'
)
$code = Invoke-ArdiaMsvcTask -BodyLines $body -TaskLabel 'launcher'
if ($code -ne 0) { throw "MSVC compilation failed ($code)" }
if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) { throw 'No compiled launcher EXE' }
Write-Host "WINDOWS-COMPILED: real portable launcher at $Output"
