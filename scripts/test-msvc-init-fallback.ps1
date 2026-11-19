# Confirm that failed Visual Studio initialization uses a separate cmd.exe,
# preserves diagnostic output, and falls back exactly once when authorized.
# The fixtures are NOT fake compilers and cannot satisfy the real MSVC preflight.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$base = $env:RUNNER_TEMP
if (-not $base) { $base = [IO.Path]::GetTempPath() }
$dir = Join-Path $base 'Ardia MSVC initializer fixture with spaces'
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$fail = Join-Path $dir 'failed initializer.bat'
$good = Join-Path $dir 'successful initializer.bat'
@('@echo off','echo Fixture: first initializer deliberately failed','exit /b 9') | Set-Content -LiteralPath $fail -Encoding ascii
@('@echo off','set "ARDIA_FAKE_SETUP_FIXTURE=success"','exit /b 0') | Set-Content -LiteralPath $good -Encoding ascii
$candidates = @(
    [pscustomobject]@{Label='fixture primary';Path=$fail;Parameters=''},
    [pscustomobject]@{Label='fixture secondary';Path=$good;Parameters=''}
)
$code = Invoke-ArdiaBatchWithFallback -Initializers $candidates -TaskLabel 'fixture' -BodyLines @(
    'if not "%ARDIA_FAKE_SETUP_FIXTURE%"=="success" exit /b 23',
    'exit /b 0'
)
if ($code -ne 0) { throw 'MSVC initializer fallback fixture did not use successful second candidate.' }
try {
    [void](Invoke-ArdiaBatchWithFallback -Initializers @($candidates[0]) -TaskLabel 'fixture-fail' -BodyLines @('exit /b 0'))
    throw 'Expected all-initializers-failed exception was not raised.'
} catch {
    if ($_.Exception.Message -notmatch 'all supported Visual Studio initializers') { throw }
}
Write-Host 'AUTOMATED-RUNTIME-TESTED (runner): independent initializer fallback and fail-closed behavior passed (fixtures only).'
