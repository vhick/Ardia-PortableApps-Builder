param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
$p = (Resolve-Path -LiteralPath $Installer).Path
$b = [System.IO.File]::ReadAllBytes($p)
if ($b.Length -lt 100000 -or $b[0] -ne 0x4d -or $b[1] -ne 0x5a) { throw 'Installer not a real Windows PE or implausibly small' }
$offset = [BitConverter]::ToInt32($b, 0x3c)
if ($offset -lt 64 -or $offset -gt ($b.Length-6) -or $b[$offset] -ne 0x50 -or $b[$offset+1] -ne 0x45) { throw 'Bad installer PE structure' }
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()
Write-Host "STATIC installer validated: $p SHA256=$sha; installation/upgrade execution NOT verified"
