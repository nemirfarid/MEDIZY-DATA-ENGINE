# Helper: dump a line range of a file to an output file (avoids shell integration capture issues)
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [int]$Skip = 0,
  [int]$First = 0,
  [Parameter(Mandatory = $true)][string]$Out
)

$lines = Get-Content -LiteralPath $Path -Encoding UTF8
if ($Skip -gt 0) { $lines = $lines | Select-Object -Skip $Skip }
if ($First -gt 0) { $lines = $lines | Select-Object -First $First }
$i = $Skip
foreach ($l in $lines) {
  $i++
  "$i | $l" | Out-File -FilePath $Out -Append -Encoding UTF8
}
"DONE" | Out-File -FilePath $Out -Append -Encoding UTF8
