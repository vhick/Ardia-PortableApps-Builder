# CI preflight -- fail before downloading the large Chromium setup when
# GitHub's image does not actually provide a working x64 MSVC compiler.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$vc = Find-ArdiaMsvcVcvars
$batch = Join-Path $env:RUNNER_TEMP 'ardia-msvc-preflight.cmd'
$source = Join-Path $env:RUNNER_TEMP 'ardia-msvc-preflight.cpp'
$binary = Join-Path $env:RUNNER_TEMP 'ardia-msvc-preflight.exe'
'int main() { return 0; }' | Set-Content -LiteralPath $source -Encoding utf8
@(
    '@echo off',
    'chcp 65001 >nul',
    'call "'+$vc+'" >nul',
    'if errorlevel 1 exit /b 21',
    'where.exe cl.exe >nul 2>&1',
    'if errorlevel 1 exit /b 22',
    'cl.exe /nologo /EHsc /Fe:"'+$binary+'" "'+$source+'" /link /SUBSYSTEM:CONSOLE',
    'if errorlevel 1 exit /b 23',
    '"'+$binary+'"',
    'exit /b %ERRORLEVEL%'
) | Set-Content -LiteralPath $batch -Encoding utf8
& cmd.exe /d /c ('"'+$batch+'"')
$code = $LASTEXITCODE
if ($code -ne 0) { throw "MSVC preflight failed ($code). Check the selected GitHub runner image and VC tools." }
Write-Host 'MSVC x64 preflight passed; launcher tests and source build may proceed.'
