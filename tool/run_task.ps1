# Helper: run a named task fully detached so it survives terminal closure.
# Each task has a fixed argument list, avoiding all shell quoting issues.
param(
  [Parameter(Mandatory = $true)][string]$Task
)

$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:PATH"

$tasks = @{
  'analyze'      = @{ exe = 'flutter'; args = @('analyze', '--no-pub'); out = 'tmp_analyze.txt' }
  'test'         = @{ exe = 'flutter'; args = @('test', '--no-pub'); out = 'tmp_test.txt' }
  'testone'      = @{ exe = 'flutter'; args = @('test', '--no-pub'); out = 'tmp_test.txt' }
  'format'       = @{ exe = 'dart'; args = @('format', '--output=none', '--set-exit-if-changed', '.'); out = 'tmp_format.txt' }
  'audit'        = @{ exe = 'dart'; args = @('run', 'tool/category_audit.dart', 'tmp_audit_v1.txt'); out = 'tmp_audit_run.txt' }
  'cats'         = @{ exe = 'dart'; args = @('run', 'tool/check_categories.dart'); out = 'tmp_cats.txt' }
  'probe'        = @{ exe = 'dart'; args = @('--version'); out = 'tmp_probe.txt' }
}

if (-not $tasks.ContainsKey($Task)) {
  "UNKNOWN TASK: $Task" | Out-File -FilePath (Join-Path $projectRoot 'tmp_launch.txt') -Encoding UTF8
  exit 1
}

$t = $tasks[$Task]
$outFile = Join-Path $projectRoot $t.out
$errFile = Join-Path $projectRoot ($t.out + '.err')
foreach ($f in @($outFile, $errFile)) {
  if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force }
}

$p = Start-Process -FilePath $t.exe -ArgumentList $t.args -WorkingDirectory $projectRoot `
  -RedirectStandardOutput $outFile -RedirectStandardError $errFile `
  -NoNewWindow -PassThru

"LAUNCHED TASK=$Task PID=$($p.Id) CMD=$($t.exe) $($t.args -join ' ')" |
  Out-File -FilePath (Join-Path $projectRoot 'tmp_launch.txt') -Encoding UTF8
