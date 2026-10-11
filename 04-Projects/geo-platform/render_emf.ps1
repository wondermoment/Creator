param([Parameter(Mandatory=$true)][string]$InputFile,[Parameter(Mandatory=$true)][string]$OutputFile)
Add-Type -AssemblyName System.Drawing
$metafile = [System.Drawing.Image]::FromFile($InputFile)
try {
    $scale = [Math]::Min(3.0, 4096.0 / [Math]::Max($metafile.Width, $metafile.Height))
    $width = [Math]::Max(1, [int]($metafile.Width * $scale))
    $height = [Math]::Max(1, [int]($metafile.Height * $scale))
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    try {
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try { $graphics.Clear([System.Drawing.Color]::White); $graphics.DrawImage($metafile, 0, 0, $width, $height) }
        finally { $graphics.Dispose() }
        $bitmap.Save($OutputFile, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally { $bitmap.Dispose() }
} finally { $metafile.Dispose() }
