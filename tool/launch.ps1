# Helper: launch a detached background process with redirected stdout/stderr.
# Survives the interactive terminal being closed.
param(
  [Parameter(Mandatory = $true)][string]$Exe,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$ArgLine = ''
)

$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$outFile = Join-Path $projectRoot $Out
$errFile = Join-Path $projectRoot ($Out + '.err')
if (Test-Path -LiteralPath $outFile) { Remove-Item -LiteralPath $outFile -Force }
if (Test-Path -LiteralPath $errFile) { Remove-Item -LiteralPath $errFile -Force }

$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:PATH"

$argList = @()
if ($ArgLine.Trim().Length -gt 0) { $argList = $ArgLine.Trim() -split '\s+' }
$p = Start-Process -FilePath $Exe -ArgumentList $argList -WorkingDirectory $projectRoot `
  -RedirectStandardOutput $outFile -RedirectStandardError $errFile `
  -NoNewWindow -PassThru

"LAUNCHED PID=$($p.Id)" | Out-File -FilePath (Join-Path $projectRoot 'tmp_launch.txt') -Encoding UTF8
