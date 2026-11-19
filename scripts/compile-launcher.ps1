param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$vc = Find-ArdiaMsvcVcvars
$dir = Split-Path -Parent $Output
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$batch = Join-Path $env:RUNNER_TEMP 'compile-ardia.cmd'
# Compiler environment must be initialized in the SAME cmd.exe process.
@(
    '@echo off',
    'chcp 65001 >nul',
    'call "'+$vc+'" >nul',
    'if errorlevel 1 exit /b 21',
    'where.exe cl.exe >nul 2>&1',
    'if errorlevel 1 exit /b 22',
    'cl.exe /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE /MT /Fe:"'+$Output+'" "'+$Source+'" /link /SUBSYSTEM:WINDOWS shell32.lib',
    'exit /b %ERRORLEVEL%'
) | Set-Content -LiteralPath $batch -Encoding utf8
$code = Invoke-ArdiaMsvcBatch -Script $batch
if ($code -ne 0) { throw "MSVC compilation failed ($code)" }
if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) { throw 'No compiled launcher EXE' }
Write-Host "WINDOWS-COMPILED: real portable launcher at $Output"
