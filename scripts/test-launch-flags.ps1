# Unit-test launch argument defaults with the same MSVC toolchain as the launcher.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$vc = Find-ArdiaMsvcVcvars
$src = Join-Path $env:GITHUB_WORKSPACE 'tests\test_launch_flags.cpp'
$exe = Join-Path $env:RUNNER_TEMP 'test_ardia_launch_flags.exe'
$batch = Join-Path $env:RUNNER_TEMP 'test-ardia-flags.cmd'
@(
    '@echo off',
    'chcp 65001 >nul',
    'call "'+$vc+'" >nul',
    'if errorlevel 1 exit /b 21',
    'where.exe cl.exe >nul 2>&1',
    'if errorlevel 1 exit /b 22',
    'cl.exe /nologo /std:c++17 /EHsc /W4 /WX /Fe:"'+$exe+'" "'+$src+'" /link /SUBSYSTEM:CONSOLE',
    'if errorlevel 1 exit /b 23',
    '"'+$exe+'"',
    'exit /b %ERRORLEVEL%'
) | Set-Content -LiteralPath $batch -Encoding utf8
& cmd.exe /d /c ('"'+$batch+'"')
$code = $LASTEXITCODE
if ($code -ne 0) { throw "Launcher defaults unit tests failed ($code)" }
Write-Host 'AUTOMATED: six launcher argument defaults, forwarding and opt-out passed with MSVC.'
