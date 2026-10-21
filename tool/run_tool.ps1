# Helper: run a flutter/dart command with a guaranteed PATH (git included) and capture output to a file.
param(
  [Parameter(Mandatory = $true)][string]$Exe,          # 'flutter' or 'dart'
  [Parameter(Mandatory = $true)][string]$Out,          # output file
  [string[]]$Args = @()                                # extra args
)

$projectRoot = 'C:\SANTE_DZ_SCRAPER'
$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;$env:PATH"

$argList = @($Args)
$outFile = Join-Path $projectRoot $Out

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
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
$p.WaitForExit()

($stdout + "`n" + $stderr) | Out-File -FilePath $outFile -Encoding UTF8
"EXITCODE: $($p.ExitCode)" | Out-File -FilePath $outFile -Append -Encoding UTF8
'DONE' | Out-File -FilePath $outFile -Append -Encoding UTF8
