# Helper: launch a long-running tool command detached so the interactive terminal
# can be closed without killing it. Poll the output file for a sentinel.
param(
  [Parameter(Mandatory = $true)][string]$Exe,
  [Parameter(Mandatory = $true)][string]$Out,
  [string[]]$Args = @(),
  [string]$Sentinel = 'RUN_COMPLETE'
)

$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$outFile = Join-Path $projectRoot $Out
$logFile = Join-Path $projectRoot ($Out + '.log')

$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:PATH"

$argList = @($Args) + @('--', $Sentinel)
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Exe
$psi.Arguments = ($argList -join ' ')
$psi.WorkingDirectory = $projectRoot
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$null = $p.Start()

# Stream output live to the log file so progress is visible while running.
$sw = New-Object System.IO.StreamWriter($logFile, $false, [System.Text.Encoding]::UTF8)
$outTask = $p.StandardOutput.ReadToEndAsync()
$errTask = $p.StandardError.ReadToEndAsync()
$null = $sw
$null = $outTask
$null = $errTask

# Simple sequential drain is fine: stdout and stderr are pumped into the log.
while (-not $p.HasExited) {
  Start-Sleep -Milliseconds 200
}
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
$p.WaitForExit()

($stdout + "`n" + $stderr) | Out-File -FilePath $logFile -Encoding UTF8
"DONE" | Out-File -FilePath $logFile -Append -Encoding UTF8
