# Helper: recursive regex search over a source tree, results written to a file.
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [Parameter(Mandatory = $true)][string]$Pattern,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Filter = '*.dart'
)

$rootFull = (Resolve-Path -LiteralPath $Root).Path
$results = Get-ChildItem -LiteralPath $rootFull -Recurse -File -Filter $Filter |
  Select-String -Pattern $Pattern

$results | ForEach-Object {
  $rel = $_.Path.Substring($rootFull.Length + 1)
  "$rel : $($_.LineNumber) : $($_.Line.Trim())"
} | Out-File -FilePath $Out -Encoding UTF8

"TOTAL MATCHES: $($results.Count)" | Out-File -FilePath $Out -Append -Encoding UTF8
"DONE" | Out-File -FilePath $Out -Append -Encoding UTF8
