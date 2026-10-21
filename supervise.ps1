# Superviseur de campagne SANTE DZ / MEDIZY
# Relance scraper.py automatiquement tant que les 58 wilayas ne sont pas
# toutes terminees. Ne modifie aucun code du scraper.
$ErrorActionPreference = "Continue"
$root    = "C:\SANTE_DZ_SCRAPER"
$exp     = "D:\SANTE_DZ_EXPORTS"
$log     = Join-Path $root "run.log"
$scr     = Join-Path $root "scraper.py"
$totalWilayas = 58

function Get-Etat {
    $f = Join-Path $exp "progression.json"
    if (-not (Test-Path -LiteralPath $f)) { return $null }
    try { return Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

$cycle = 0
while ($true) {
    $cycle++
    Write-Output "=== CYCLE $cycle - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

    # Nettoyage des Chrome orphelins : sans cela le service reseau du
    # navigateur tombe en ERR_INTERNET_DISCONNECTED apres quelques heures.
    $chrome = Get-Process chrome -ErrorAction SilentlyContinue
    if ($chrome) {
        Write-Output "[SUP] $($chrome.Count) processus chrome residuels -> purge"
        $chrome | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
    }

    $args = @("-u","scraper.py","--all","--max-results","80","--max-retries","3",
              "--base-delay","3","--delay","3","--visible","--resume")

    Push-Location $root
    & "C:\Python314\python.exe" @args *>> $log
    $code = $LASTEXITCODE
    Pop-Location

    Write-Output "[SUP] scraper termine (code=$code)"

    $etat = Get-Etat
    if ($etat) {
        $pairs = @($etat.completed).Count
        Write-Output "[SUP] paires completes : $pairs"
    }

    $sp = Join-Path $exp "scraping_progress.json"
    if (Test-Path -LiteralPath $sp) {
        try {
            $s = Get-Content -LiteralPath $sp -Raw -Encoding UTF8 | ConvertFrom-Json
            $n = @($s.wilayas_terminees).Count
            Write-Output "[SUP] wilayas terminees : $n / $totalWilayas"
            if ($n -ge $totalWilayas) {
                Write-Output "[SUP] CAMPAGNE TERMINEE - toutes les wilayas sont validees"
                break
            }
        } catch {}
    }

    Write-Output "[SUP] pause 20s avant relance"
    Start-Sleep -Seconds 20
}
Write-Output "=== SUPERVISION FINIE $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
