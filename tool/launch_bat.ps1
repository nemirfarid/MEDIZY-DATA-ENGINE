# Helper: fully detached launch of a .bat wrapper (survives terminal closure).
param(
  [Parameter(Mandatory = $true)][string]$ArgLine,
  [string]$Bat = 'tool\run_fx.bat'
)

$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:PATH"
$batFull = Join-Path $projectRoot $Bat

$p = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c `"$batFull`" $ArgLine" `
  -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

"LAUNCHED PID=$($p.Id) ARGS=$ArgLine" |
  Out-File -FilePath (Join-Path $projectRoot 'tmp_launch.txt') -Encoding UTF8
