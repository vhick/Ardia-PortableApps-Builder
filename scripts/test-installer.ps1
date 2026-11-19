# Headless custom-NSIS installer smoke test on a disposable GitHub-hosted Windows runner ONLY.
# Pinned UPB v1.0.0 intentionally installs App/Other/launcher and creates ONLY Data/.
# It does not copy the empty layout directories from the validated ready-to-extract ZIP.
# The compiled root launcher creates selected Data subdirectories on FIRST browser launch.
# Headless installer testing therefore seeds BOTH layout folders as a fixture AFTER the
# fresh install, and proves that a same-version reinstall leaves existing data untouched.
param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [ValidateSet('windows-appdata-mirror-v2','legacy-profile-v1')]
    [string]$Layout='windows-appdata-mirror-v2'
)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Installer test is GitHub-hosted Windows runner only'
}
$resolved = (Resolve-Path -LiteralPath $Installer).Path
$dest = Join-Path $env:RUNNER_TEMP 'ArdiaPortable-Paf-InstallerTest'
if (Test-Path -LiteralPath $dest) { throw 'Refusing nonfresh isolated installer test destination' }

function Install-Test {
    $p = [Diagnostics.ProcessStartInfo]::new()
    $p.FileName = $resolved
    # NSIS: /S (case sensitive); /D=full-path must be last and unquoted.
    $p.Arguments = "/S /D=$dest"
    $p.UseShellExecute = $false
    $p.CreateNoWindow = $true
    $pr = [Diagnostics.Process]::Start($p)
    try {
        if (!$pr.WaitForExit(240000)) { $pr.Kill(); throw 'Timed out during headless installer smoke test' }
        if ($pr.ExitCode -ne 0) { throw "Installer smoke exit code $($pr.ExitCode)" }
    } finally { $pr.Dispose() }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'ArdiaPortable.exe') -PathType Leaf)) {
        throw 'Installer did not write root launcher to intended destination'
    }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'App/Ardia/Ardia.exe') -PathType Leaf)) {
        throw 'Installer did not write upstream Ardia.exe'
    }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'App/AppInfo/appinfo.ini') -PathType Leaf)) {
        throw 'Installer did not include metadata'
    }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'Data') -PathType Container)) {
        throw 'Pinned installer did not create the top-level Data folder'
    }
    if (!(Test-Path -LiteralPath (Join-Path $dest 'Other/Source/data-layout.json') -PathType Leaf)) {
        throw 'Installer omitted compiled Data layout manifest'
    }
    $manifest = Get-Content -LiteralPath (Join-Path $dest 'Other/Source/data-layout.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.layout -ne $Layout) {
        throw "Installed layout manifest mismatch: expected '$Layout' but got '$($manifest.layout)'"
    }
}

Install-Test
# The installer should NOT be expected to populate selected empty subdirectories.
# Verify real, documented installer contract before simulating first-launch layout creation.
if ($Layout -eq 'windows-appdata-mirror-v2') {
    $required = Join-Path $dest 'Data/Roaming/Ardia'
    $profileRoot = Join-Path $dest 'Data/Local/Ardia/User Data'
    $unexpected = Join-Path $dest 'Data/Profile'
} else {
    $required = Join-Path $dest 'Data/Profile'
    $profileRoot = $required
    $unexpected = Join-Path $dest 'Data/Local/Ardia/User Data'
}
if (Test-Path -LiteralPath $unexpected) { throw 'Installer populated the other Data layout unexpectedly' }
if (Test-Path -LiteralPath $required) { throw 'Installer unexpectedly created layout subdirectories; review pinned builder contract' }

# Controlled fixture: model the layout that the real root launcher creates on first run.
# This is NOT evidence that the actual browser ran or retained its profile.
New-Item -Path $required -ItemType Directory -Force | Out-Null
New-Item -Path $profileRoot -ItemType Directory -Force | Out-Null
$empty = Join-Path $profileRoot 'Empty/Nested/Leaves'
New-Item -Path $empty -ItemType Directory -Force | Out-Null
$marker = Join-Path $dest 'Data/profile-preservation-marker-ユニコード.txt'
[System.IO.File]::WriteAllText($marker, 'Do not overwrite original Data', [System.Text.UTF8Encoding]::new($false))
$hash = (Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash

Install-Test
if (!(Test-Path -LiteralPath $required -PathType Container)) { throw 'Reinstall removed selected layout directory' }
if (!(Test-Path -LiteralPath $profileRoot -PathType Container)) { throw 'Reinstall removed selected profile root' }
if (!(Test-Path -LiteralPath $empty -PathType Container)) { throw 'Reinstall removed an empty nested Data directory' }
if (!(Test-Path -LiteralPath $marker -PathType Leaf)) { throw 'Reinstall removed seeded user Data' }
if ((Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash -ne $hash) { throw 'Reinstall changed seeded user Data' }
if (Test-Path -LiteralPath $unexpected) { throw 'Reinstall created the wrong Data layout' }
Write-Host 'AUTOMATED-RUNTIME-TESTED (installer only): fresh installation created Data root; same-version reinstall preserved simulated selected-layout profile folders, empty nested folders, and seeded user file.'
Write-Host 'NOT VERIFIED: actual browser first-launch folder creation, interactive GUI, host trace confinement, cross-version upgrade, or rollback.'
