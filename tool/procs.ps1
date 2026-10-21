# Helper: report whether a flutter/dart process is still running.
$procs = Get-Process -Name 'dart', 'flutter' -ErrorAction SilentlyContinue
$out = 'C:\SANTE_DZ_SCRAPER\tmp_procs.txt'
$lines = @()
if ($procs) {
  foreach ($p in $procs) { $lines += "$($p.ProcessName) PID=$($p.Id) CPU=$($p.CPU) Start=$($p.StartTime)" }
} else {
  $lines += 'no dart/flutter process running'
}
$lines | Out-File -FilePath $out -Encoding UTF8
'DONE' | Out-File -FilePath $out -Append -Encoding UTF8
