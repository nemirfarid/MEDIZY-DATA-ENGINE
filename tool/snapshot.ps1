# Helper: copy a file to a fresh timestamped name so the reader never serves a stale cache.
param(
  [Parameter(Mandatory = $true)][string]$Src,
  [Parameter(Mandatory = $true)][string]$Out
)
$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$srcPath = Join-Path $projectRoot $Src
$outPath = Join-Path $projectRoot $Out
if (Test-Path -LiteralPath $srcPath) {
  $content = Get-Content -LiteralPath $srcPath -Raw -Encoding UTF8
  $info = "SIZE: $((Get-Item -LiteralPath $srcPath).Length) bytes`n"
  ($info + $content) | Out-File -FilePath $outPath -Encoding UTF8
} else {
  "MISSING: $srcPath" | Out-File -FilePath $outPath -Encoding UTF8
}
'DONE' | Out-File -FilePath $outPath -Append -Encoding UTF8
