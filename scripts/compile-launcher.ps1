param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference='Stop'
$vswhere="${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if(-not(Test-Path -LiteralPath $vswhere)){throw 'vswhere missing from hosted Windows runner'}
$vs=(& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
if($LASTEXITCODE -ne 0 -or -not $vs){throw 'MSVC C++ build tools unavailable'}
$batch=Join-Path $env:RUNNER_TEMP 'compile-ardia.cmd'
$vc=Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
if(-not(Test-Path -LiteralPath $vc)){throw 'vcvars64.bat missing'}
$dir=Split-Path -Parent $Output;New-Item -ItemType Directory -Force -Path $dir|Out-Null
# cmd script avoids losing MSVC environment between PowerShell processes.
@('@echo off', 'call "'+$vc+'" >nul', 'if errorlevel 1 exit /b 1', 'cl.exe /nologo /std:c++17 /EHsc /O2 /W4 /DUNICODE /D_UNICODE /MT /Fe:"'+$Output+'" "'+$Source+'" /link /SUBSYSTEM:WINDOWS shell32.lib', 'exit /b %ERRORLEVEL%') | Set-Content -LiteralPath $batch -Encoding ascii
& cmd.exe /d /c ('"'+$batch+'"')
if($LASTEXITCODE -ne 0){throw "MSVC compilation failed ($LASTEXITCODE)"}
if(-not(Test-Path -LiteralPath $Output)){throw 'No compiled launcher EXE'}
