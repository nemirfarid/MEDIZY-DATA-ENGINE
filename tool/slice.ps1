param(
  [Parameter(Mandatory = $true)][string]$Src,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$Skip = 0,
  [int]$First = 0
)
$root = 'C:\SANTE_DZ_SCRAPER'
$srcPath = Join-Path $root $Src
$outPath = Join-Path $root $Out
$lines = Get-Content -LiteralPath $srcPath
if ($First -gt 0) { $lines = $lines | Select-Object -Skip $Skip -First $First }
else { $lines = $lines | Select-Object -Skip $Skip }
$header = "SIZE: $((Get-Item -LiteralPath $srcPath).Length) bytes | LINES: $($lines.Count) | OFFSET: $Skip`n"
Set-Content -LiteralPath $outPath -Value ($header + ($lines -join "`n") + "`nDONE") -Encoding UTF8
