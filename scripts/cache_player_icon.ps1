param([string]$Executable, [string]$Destination)
Add-Type -AssemblyName System.Drawing
$playerIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($Executable)
if ($null -ne $playerIcon) {
    $playerBitmap = $playerIcon.ToBitmap()
    try { $playerBitmap.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png) }
    finally { $playerBitmap.Dispose(); $playerIcon.Dispose() }
}
