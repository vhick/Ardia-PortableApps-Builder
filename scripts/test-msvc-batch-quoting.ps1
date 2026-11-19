# Standalone early regression check: no C++ compiler required.
# Exercises CMD /S /C with spaces in BOTH the batch path and target path,
# and confirms that a deliberate child exit code is propagated exactly.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'msvc-tools.ps1')
$folder = Join-Path $env:RUNNER_TEMP 'Ardia CMD quoting test with spaces'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$batch = Join-Path $folder 'check cmd batch path.cmd'
$sentinel = Join-Path $folder 'cmd executed correctly.txt'
$quotedSentinel = '"' + $sentinel + '"'
if (Test-Path -LiteralPath $sentinel) { Remove-Item -LiteralPath $sentinel -Force }
@(
  '@echo off'
  "echo correct > $quotedSentinel"
  'exit /b 0'
) | Set-Content -LiteralPath $batch -Encoding ascii
$code = Invoke-ArdiaMsvcBatch -Script $batch
if ($code -ne 0 -or -not (Test-Path -LiteralPath $sentinel -PathType Leaf)) {
  throw "Batch quoting regression: batch was not correctly invoked (exit $code)"
}
@('@echo off', 'exit /b 42') | Set-Content -LiteralPath $batch -Encoding ascii
$code = Invoke-ArdiaMsvcBatch -Script $batch
if ($code -ne 42) { throw "Batch exit-code propagation regression: expected 42, received $code" }
Remove-Item -LiteralPath $folder -Recurse -Force
Write-Host 'AUTOMATED-RUNTIME-TESTED (runner): CMD quoting with spaces and exit-code propagation passed.'
