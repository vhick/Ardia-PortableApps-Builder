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
