# Run platform-independent C++ launch-argument tests under the actual MSVC
# toolchain used by the Windows launcher, without launching a GUI browser.
$ErrorActionPreference='Stop'
$vswhere="${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if(-not(Test-Path -LiteralPath $vswhere)){throw 'Visual Studio build tools locator not found'}
$vs=(& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
if($LASTEXITCODE -ne 0 -or -not $vs){throw 'MSVC C++ compiler is unavailable'}
$vc=Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
if(-not(Test-Path -LiteralPath $vc)){throw 'Missing vcvars64.bat'}
$src=Join-Path $env:GITHUB_WORKSPACE 'tests\test_launch_flags.cpp'
$exe=Join-Path $env:RUNNER_TEMP 'test_ardia_launch_flags.exe'
$batch=Join-Path $env:RUNNER_TEMP 'test-ardia-flags.cmd'
@('@echo off', 'call "'+$vc+'" >nul', 'if errorlevel 1 exit /b 1',
  'cl.exe /nologo /std:c++17 /EHsc /W4 /WX /Fe:"'+$exe+'" "'+$src+'" /link /SUBSYSTEM:CONSOLE',
  'if errorlevel 1 exit /b 1', '"'+$exe+'"', 'exit /b %ERRORLEVEL%') |
  Set-Content -LiteralPath $batch -Encoding ascii
& cmd.exe /d /c ('"'+$batch+'"')
if($LASTEXITCODE -ne 0){throw "Launcher defaults unit tests failed ($LASTEXITCODE)"}
Write-Host 'AUTOMATED: six launcher argument defaults, forwarding and opt-out passed'
