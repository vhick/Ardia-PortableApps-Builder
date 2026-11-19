# Shared MSVC 64-bit toolchain locator for Ardia PortableApps CI.
# Do not assume a Visual Studio year or a fixed installation directory.
# The pinned windows-2022 runner includes Visual Studio 2022 and VC x64 tools.
Set-StrictMode -Version Latest

function Find-ArdiaMsvcVcvars {
    [CmdletBinding()]
    param()
    $search = [System.Collections.Generic.List[string]]::new()
    $locator = $null
    if (${env:ProgramFiles(x86)}) {
        $path = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
        if (Test-Path -LiteralPath $path -PathType Leaf) { $locator = $path }
    }
    if (-not $locator) {
        $command = Get-Command 'vswhere.exe' -ErrorAction SilentlyContinue
        if ($command) { $locator = $command.Source }
    }
    if (-not $locator) {
        throw 'MSVC preflight: vswhere.exe was not found. The runner must provide Visual Studio C++ build tools.'
    }

    # First use the documented VC component. Some VS images change their
    # component identifiers: also enumerate ALL products and inspect cl.exe.
    $queries = @(
        ,@('-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath')
        ,@('-all', '-products', '*', '-property', 'installationPath')
    )
    foreach ($arguments in $queries) {
        $entries = @(& $locator @arguments)
        $result = $LASTEXITCODE # Capture immediately: PowerShell pipelines may reset it.
        if ($result -ne 0) { throw "vswhere returned exit code $result. Cannot safely select a compiler." }
        foreach ($entry in $entries) {
            $installation = ([string]$entry).Trim()
            if ($installation -and -not $search.Contains($installation)) { $search.Add($installation) }
        }
    }
    foreach ($installation in $search) {
        $vcvars = Join-Path $installation 'VC\Auxiliary\Build\vcvars64.bat'
        $toolsets = Join-Path $installation 'VC\Tools\MSVC'
        if (-not (Test-Path -LiteralPath $vcvars -PathType Leaf)) { continue }
        if (-not (Test-Path -LiteralPath $toolsets -PathType Container)) { continue }
        # vcvars64.bat alone is not proof of an installed working C++ compiler.
        $compilerFound = $false
        foreach ($version in @(Get-ChildItem -LiteralPath $toolsets -Directory -ErrorAction SilentlyContinue)) {
            $compiler = Join-Path $version.FullName 'bin\Hostx64\x64\cl.exe'
            if (Test-Path -LiteralPath $compiler -PathType Leaf) {
                $compilerFound = $true
                break
            }
        }
        if (-not $compilerFound) { continue }
        Write-Host "MSVC toolchain found: $installation"
        return $vcvars
    }
    throw 'MSVC preflight: no complete x64 VC toolchain found. Checked Visual Studio installations via vswhere (strict and unfiltered queries).'
}


# Run a generated .cmd file without PowerShell 7 native-argument re-quoting.
# cmd.exe /D /S /C must receive the DOUBLE-wrapped batch path unchanged:
# /D /S /C ""C:\path with spaces\script.cmd""
# Using ProcessStartInfo.Arguments (not PowerShell's native invocation parser)
# makes this identical in PowerShell 7.2/7.4 and under paths containing spaces.
function Invoke-ArdiaMsvcBatch {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Script)
    $resolved = (Resolve-Path -LiteralPath $Script -ErrorAction Stop).ProviderPath
    if ([IO.Path]::GetExtension($resolved) -ine '.cmd') {
        throw "Refusing to run a non-CMD script as a compiler batch: $resolved"
    }
    if ($resolved.Contains('"')) { throw 'Invalid CMD script path contains quotation marks' }

    $shell = $env:ComSpec
    if (-not $shell) { $shell = Join-Path $env:SystemRoot 'System32\cmd.exe' }
    if (-not (Test-Path -LiteralPath $shell -PathType Leaf)) {
        throw "Windows command interpreter missing: $shell"
    }
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $shell
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    # Intentionally retain BOTH outer quote characters: cmd /S removes the
    # first and last quote, leaving the inner quoted batch filename intact.
    $start.Arguments = '/D /S /C ""' + $resolved + '""'
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw "Could not launch CMD for $resolved" }
        $process.WaitForExit()
        return [int]$process.ExitCode
    }
    finally { $process.Dispose() }
}


# Use Microsoft's documented VS2022 initialization methods, in isolated
# command processes.  A previous runner had a real cl.exe but vcvars64.bat
# returned nonzero; NEVER hide the diagnostic output when that happens.
function Get-ArdiaMsvcInitializers {
    [CmdletBinding()]
    param()
    $vcvars = Find-ArdiaMsvcVcvars
    $vsRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $vcvars)))
    $devCmd = Join-Path $vsRoot 'Common7\Tools\VsDevCmd.bat'
    $candidates = [System.Collections.Generic.List[object]]::new()
    if (Test-Path -LiteralPath $devCmd -PathType Leaf) {
        $candidates.Add([pscustomobject]@{
            Label = 'VsDevCmd x64'
            Path = $devCmd
            Parameters = '-arch=amd64 -host_arch=amd64 -no_logo'
        })
    }
    if (Test-Path -LiteralPath $vcvars -PathType Leaf) {
        $candidates.Add([pscustomobject]@{
            Label = 'vcvars64 x64'
            Path = $vcvars
            Parameters = ''
        })
    }
    if ($candidates.Count -eq 0) {
        throw 'MSVC preflight: Neither VsDevCmd.bat nor vcvars64.bat exists in the selected Visual Studio installation.'
    }
    return $candidates.ToArray()
}

# General, source-readable fallback engine.  Each initializer gets a NEW
# cmd.exe process; a partially initialized failed environment cannot leak
# into the following attempt.  Fallback only for setup/availability failure,
# never for compiler, linker, or test failures.
function Invoke-ArdiaBatchWithFallback {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][object[]]$Initializers,
        [Parameter(Mandatory)][string[]]$BodyLines,
        [Parameter(Mandatory)][string]$TaskLabel
    )
    if ($Initializers.Count -eq 0) { throw 'No Visual Studio initializers were supplied.' }
    if ($TaskLabel -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid task identifier.' }
    $base = $env:RUNNER_TEMP
    if (-not $base) { $base = [IO.Path]::GetTempPath() }
    $work = Join-Path $base 'Ardia MSVC init with spaces'
    New-Item -ItemType Directory -Path $work -Force | Out-Null
    $index = 0
    foreach ($initializer in $Initializers) {
        $index += 1
        $initPath = [string]$initializer.Path
        $params = [string]$initializer.Parameters
        $label = [string]$initializer.Label
        if (-not (Test-Path -LiteralPath $initPath -PathType Leaf)) {
            Write-Warning "Missing MSVC initializer: $label at $initPath"
            continue
        }
        if ($initPath.Contains('"') -or $initPath.Contains([char]13) -or $initPath.Contains([char]10)) {
            throw 'Unsafe Visual Studio initializer path.'
        }
        # /D prevents cmd AutoRun interference.  No global environment,
        # registry, PATH or installed application settings are modified.
        $cmdPath = Join-Path $work ("ardia-$TaskLabel-$index.cmd")
        $lines = @(
            '@echo off',
            'setlocal EnableExtensions DisableDelayedExpansion',
            'chcp 65001 >nul',
            'set "VSCMD_SKIP_SENDTELEMETRY=1"',
            ('echo Ardia: initializing MSVC with ' + $label),
            ('call "' + $initPath + '" ' + $params),
            'if errorlevel 1 (',
            '  echo Ardia: Visual Studio initializer reported failure.',
            '  exit /b 21',
            ')'
        ) + @($BodyLines)
        # pwsh 7: UTF8 means UTF-8 without BOM; non-ASCII filenames survive
        # after chcp 65001.  Using ASCII would corrupt Unicode paths.
        $lines | Set-Content -LiteralPath $cmdPath -Encoding utf8
        $code = Invoke-ArdiaMsvcBatch -Script $cmdPath
        if ($code -eq 0) {
            Write-Host "MSVC $TaskLabel passed with $label."
            return 0
        }
        if ($code -eq 21 -or $code -eq 22) {
            Write-Warning "MSVC $TaskLabel initializer $label failed (exit $code). Trying a separate supported initialization method if available."
            continue
        }
        throw "MSVC $TaskLabel failed AFTER initialization (exit $code). No fallback, because a compiler/test failure must not be disguised."
    }
    throw "MSVC $TaskLabel failed: all supported Visual Studio initializers were unavailable or unsuccessful. Read the UNSUPPRESSED VsDevCmd/vcvars64 diagnostics immediately above."
}

function Invoke-ArdiaMsvcTask {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string[]]$BodyLines,
        [Parameter(Mandatory)][string]$TaskLabel
    )
    $initializers = @(Get-ArdiaMsvcInitializers)
    # Make actual cl.exe and link.exe availability part of the real acceptance.
    # These codes trigger a separate environment-initialization fallback.
    $toolChecks = @(
        'where.exe cl.exe >nul 2>&1',
        'if errorlevel 1 (echo Ardia: cl.exe missing after setup & exit /b 22)',
        'where.exe link.exe >nul 2>&1',
        'if errorlevel 1 (echo Ardia: link.exe missing after setup & exit /b 22)'
    )
    return Invoke-ArdiaBatchWithFallback -Initializers $initializers -BodyLines ($toolChecks + @($BodyLines)) -TaskLabel $TaskLabel
}
