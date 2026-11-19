# Headless test on disposable Windows GitHub-hosted runner ONLY.
# Tests packaged NSIS installer /S and /D semantics from pinned custom-nsis engine.
param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') { throw 'Installer test is GitHub-hosted Windows runner only' }
$resolved = (Resolve-Path -LiteralPath $Installer).Path
$dest = Join-Path $env:RUNNER_TEMP 'ArdiaPortable-Paf-InstallerTest'
if (Test-Path -LiteralPath $dest) { throw 'Refusing nonfresh isolated installer test destination' }
function Install-Test {
    $p = [Diagnostics.ProcessStartInfo]::new()
    $p.FileName = $resolved
    # NSIS: /S (case sensitive) and /D=full-path MUST be final switch and unquoted.
    $p.Arguments = "/S /D=$dest"
    $p.UseShellExecute = $false
    $p.CreateNoWindow = $true
    $pr = [Diagnostics.Process]::Start($p)
    try {
        if (!$pr.WaitForExit(240000)) { $pr.Kill(); throw 'Timed out during headless installer smoke test' }
        if ($pr.ExitCode -ne 0) { throw "Installer smoke exit code $($pr.ExitCode)" }
    } finally { $pr.Dispose() }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'ArdiaPortable.exe') -PathType Leaf)) { throw 'Installer did not write root launcher to intended destination' }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'App/Ardia/Ardia.exe') -PathType Leaf)) { throw 'Installer did not write upstream Ardia.exe' }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'App/AppInfo/appinfo.ini') -PathType Leaf)) { throw 'Installer did not include metadata' }
}
Install-Test
$empty = Join-Path $dest 'Data/Profile/Empty/Nested/Leaves'
New-Item -Path $empty -ItemType Directory -Force | Out-Null
$marker = Join-Path $dest 'Data/profile-preservation-marker-ユニコード.txt'
[System.IO.File]::WriteAllText($marker, 'Do not overwrite original Data', [System.Text.UTF8Encoding]::new($false))
$hash = (Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash
Install-Test
if (!(Test-Path -LiteralPath $empty -PathType Container)) { throw 'Completely empty nested Data directory was lost on reinstall' }
if (!(Test-Path -LiteralPath $marker -PathType Leaf)) { throw 'Seeded user Data disappeared on reinstall' }
if ((Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash -ne $hash) { throw 'Seeded user Data was overwritten' }
Write-Host 'AUTOMATED-RUNTIME-TESTED (installer only): silent fresh install and same-version reinstall on hosted runner preserved user Data and nested empty folders.'
Write-Host 'This does NOT verify desktop GUI, portable user-profile behavior, true cross-version upgrade or rollback.'
