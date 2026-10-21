# Helper: locate git and report toolchain environment, writing to a file.
$out = 'C:\SANTE_DZ_SCRAPER\tmp_git.txt'
$lines = New-Object System.Collections.Generic.List[string]

$candidates = @(
  'C:\Program Files\Git\cmd\git.exe',
  'C:\Program Files\Git\bin\git.exe',
  'C:\Program Files (x86)\Git\cmd\git.exe',
  'C:\Program Files\GitHub Desktop\app-*\resources\app\git\cmd\git.exe',
  "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe",
  'C:\tools\git\cmd\git.exe',
  'C:\src\git\cmd\git.exe'
)

$lines.Add("PATH=$env:PATH")
foreach ($c in $candidates) {
  $resolved = Resolve-Path -LiteralPath $c -ErrorAction SilentlyContinue
  if ($resolved) { $lines.Add("FOUND: $resolved") }
}
$cmd = Get-Command git.exe -ErrorAction SilentlyContinue
if ($cmd) { $lines.Add("GET-COMMAND: $($cmd.Source)") } else { $lines.Add("GET-COMMAND: not found") }

$lines.Add("--- search under C:\Program Files (depth 3) ---")
foreach ($d in @('C:\Program Files', 'C:\Program Files (x86)')) {
  if (Test-Path $d) {
    Get-ChildItem -LiteralPath $d -Recurse -Depth 3 -Filter 'git.exe' -File -ErrorAction SilentlyContinue |
      Select-Object -First 10 | ForEach-Object { $lines.Add("  $($_.FullName)") }
  }
}

$lines | Out-File -FilePath $out -Encoding UTF8
'DONE' | Out-File -FilePath $out -Append -Encoding UTF8
