# Compile and execute the unchanged Ardia C++ launch-switch regression tests.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$src = Join-Path $env:GITHUB_WORKSPACE 'tests\test_launch_flags.cpp'
$exe = Join-Path $env:RUNNER_TEMP 'test_ardia_launch_flags.exe'
$body = @(
    ('cl.exe /nologo /std:c++17 /EHsc /W4 /WX /Fe:"' + $exe + '" "' + $src + '" /link /SUBSYSTEM:CONSOLE'),
    'if errorlevel 1 (echo Ardia: launch-argument test compilation failed & exit /b 23)',
    ('"' + $exe + '"'),
    'if errorlevel 1 (echo Ardia: launch-argument tests failed & exit /b 24)',
    'exit /b 0'
)
$code = Invoke-ArdiaMsvcTask -BodyLines $body -TaskLabel 'flags'
if ($code -ne 0) { throw "Launcher defaults unit tests failed ($code)" }
Write-Host 'AUTOMATED: six launcher arguments, forwarding, duplication control and opt-out passed under MSVC.'
