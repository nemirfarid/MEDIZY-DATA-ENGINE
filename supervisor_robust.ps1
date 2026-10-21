# Superviseur robuste SANTE DZ / MEDIZY
# - Nettoie les processus chrome/node orphelins (cause d'ERR_INTERNET_DISCONNECTED).
# - Relance scraper.py en boucle tant que 58 wilayas != terminees.
# - Lancement DIRECT de python (pas de cmd /c qui casse les args) avec
#   redirection native PowerShell en UTF-8 (log léger, pas de UTF-16 2-octets).
# - Sur crash (code != 0), copie du journal pour diagnostic.
# Ne modifie PAS scraper.py.
$ErrorActionPreference = "Continue"

$root  = "C:\SANTE_DZ_SCRAPER"
$exp   = "D:\SANTE_DZ_EXPORTS"
# --- Garde single-instance ATOMIQUE (mutex nommé) ---
# Un mutex nommé est libéré automatiquement par l'OS si le superviseur est tué
# (tuiles externes), et WaitOne(0) est atomique : aucune course TOCTOU, donc aucun
# double lancement même si le cron et un wakeup se déclenchent en même temps.
# Cela évite les nœuds Playwright orphelins -> "Connection closed while reading
# from the driver" -> boucle de crash.
$mutex = New-Object System.Threading.Mutex($false, "Global\SANTE_DZ_SUPERVISOR_v1")
if (-not $mutex.WaitOne(0)) {
    Write-Host "Supervisor deja en cours (mutex detenu). Abandon pour eviter la concurrence."
    $mutex.Dispose() | Out-Null
    exit 0
}
$log   = Join-Path $root "run.log"
$supLog= Join-Path $root "supervise.log"
$total = 58
$pyExe = "C:\Python314\python.exe"

function Write-Sup([string]$t){
    $ts=Get-Date -Format "HH:mm:ss"
    $line="$ts $t"
    $line | Out-File -FilePath $supLog -Append -Encoding utf8
    Write-Output $line
}

function Get-Terminees {
    $f = Join-Path $exp "scraping_progress.json"
    if (-not (Test-Path -LiteralPath $f)) { return $null }
    try {
        $s = Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json
        return @($s.wilayas_terminees).Count
    } catch { return $null }
}

Write-Sup "=== SUPERVISOR DÉMARRÉ ==="
$cycle = 0
while ($true) {
    $cycle++
    # Rotation du journal : on garde le dernier cycle seulement.
    if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force -ErrorAction SilentlyContinue }

    # Nettoyage des orphelins chrome/node.
    $ch = Get-Process chrome -ErrorAction SilentlyContinue
    if ($ch) {
        Write-Sup "[CLEAN] $($ch.Count) processus chrome residuels supprimes"
        $ch | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 4
    }
    Get-WmiObject Win32_Process -Filter "Name='node.exe'" |
        Where-Object { $_.CommandLine -like '*playwright*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

    Write-Sup "[CYCLE $cycle] lancement scraper"

    # Lancement DIRECT avec redirection native UTF-8 (overwrite du log du cycle).
    [System.Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    & $pyExe -u scraper.py --all --max-results 80 --max-retries 6 --base-delay 3 --delay 3 --visible --resume *>> $log
    $code = $LASTEXITCODE

    # Snapshot du journal en cas d'erreur pour diagnostic.
    if ($code -ne 0) {
        $crash = Join-Path $root ("run.crash.cycle{0}.log" -f $cycle)
        if (Test-Path -LiteralPath $log) { Copy-Item -LiteralPath $log -Destination $crash -Force -ErrorAction SilentlyContinue }
        Write-Sup "[CRASH] code=$code -- snapshot -> $(Split-Path $crash -Leaf)"
    }

    $n = Get-Terminees
    Write-Sup "[CYCLE $cycle] scraper arrete (code=$code) ; wilayas_terminees=$n / $total"
    if ($n -ne $null -and $n -ge $total) {
        Write-Sup "[DONE] $n/$total wilayas terminees -> CAMPAGNE TERMINÉE, arret du superviseur"
        break
    }

    Start-Sleep -Seconds 15
}
Write-Sup "=== SUPERVISOR ARRÊTÉ ==="
try { $mutex.ReleaseMutex() | Out-Null } catch {}
$mutex.Dispose() | Out-Null
