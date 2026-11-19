param([Parameter(Mandatory=$true)][string]$Icon, [Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (!(Test-Path -LiteralPath $Icon -PathType Leaf)) { throw "Missing official icon: $Icon" }
New-Item -ItemType Directory -Path $Out -Force | Out-Null
$source = [System.Drawing.Icon]::new($Icon)
try {
    foreach ($size in @(16,32)) {
        $bmp = [System.Drawing.Bitmap]::new($size, $size)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        try {
            $g.Clear([System.Drawing.Color]::Transparent)
            $g.DrawIcon($source, [System.Drawing.Rectangle]::new(0,0,$size,$size))
            $bmp.Save((Join-Path $Out "appicon_$size.png"), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $g.Dispose(); $bmp.Dispose() }
    }
} finally { $source.Dispose() }
