<#
.SYNOPSIS
    MEDIZY / SANTE DZ - Sonde de Surveillance de Fraicheur des Sauvegardes (PowerShell)
.DESCRIPTION
    Verifie la presence d'une archive PostGIS .dump datant de moins de 26 heures,
    execute un controle d'integrite non destructif via pg_restore --list,
    genere le fichier d'etat JSON pour FastAPI et envoie une alerte Webhook en cas d'erreur.
#>

[CmdletBinding()]
param (
    [string]$BackupDir = $env:BACKUP_DIR,
    [int]$MaxAgeHours = 26,
    [string]$WebhookUrl = $env:WEBHOOK_URL
)

if (-not $BackupDir) {
    $BackupDir = "E:\medizy_data\backups"
    if (-not (Test-Path $BackupDir)) {
        $BackupDir = ".\backups"
    }
}

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "    MEDIZY - Controle de Fraicheur des Sauvegardes PostGIS (PowerShell)" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Repertoire analyse : $BackupDir"
Write-Host "Seuil maximal      : $MaxAgeHours heures"
Write-Host "Date du controle   : $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
Write-Host "=============================================================================="

function Send-Alert([string]$ErrorMsg) {
    Write-Host "ALERTE CRITIQUE : $ErrorMsg" -ForegroundColor Red

    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }

    $state = @{
        checked_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        is_valid = $false
        last_backup_timestamp = 0
        error = $ErrorMsg
    }
    $stateFile = Join-Path $BackupDir "backup_state.json"
    $state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding utf8

    if ($WebhookUrl) {
        $payloadObj = @{
            text = "ALERTE CRITIQUE SAUVEGARDE MEDIZY`nErreur : $ErrorMsg`nAction requise : Verifier backup_postgis.ps1."
        }
        $payload = $payloadObj | ConvertTo-Json
        try {
            Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $payload -ContentType "application/json" | Out-Null
        } catch {
            Write-Warning "Echec envoi Webhook : $_"
        }
    }
}

if (-not (Test-Path $BackupDir)) {
    Send-Alert "Le repertoire $BackupDir n'existe pas."
    exit 1
}

$dumpFiles = Get-ChildItem -Path $BackupDir -Filter "*.dump" | Sort-Object LastWriteTime -Descending
if ($dumpFiles.Count -eq 0) {
    Send-Alert "Aucune archive .dump trouvee dans $BackupDir."
    exit 1
}

$latestDump = $dumpFiles[0]
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$fileMtime = [DateTimeOffset]$latestDump.LastWriteTimeUtc
$fileMtimeUnix = $fileMtime.ToUnixTimeSeconds()
$ageSeconds = $now - $fileMtimeUnix
$ageHours = [Math]::Round(($ageSeconds / 3600.0), 2)
$sizeMb = [Math]::Round(($latestDump.Length / 1MB), 2)
$dumpName = $latestDump.Name
$dumpFullName = $latestDump.FullName

Write-Host "Fichier detecte : $dumpFullName"
Write-Host "Taille archive  : $sizeMb Mo"
Write-Host "Age mesure      : $ageHours heures ($ageSeconds secondes)"

if ($ageHours -gt $MaxAgeHours) {
    Send-Alert "Sauvegarde obsolete ! Age : $ageHours heures (seuil maximal : $MaxAgeHours h)."
    exit 1
}

# Controle integrite pg_restore
Write-Host "Verification integrite binaire..." -ForegroundColor Yellow
$pgRestore = Get-Command "pg_restore" -ErrorAction SilentlyContinue
if ($pgRestore) {
    & pg_restore --list $dumpFullName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Send-Alert "Corruption detectee ! Echec de pg_restore --list sur $dumpName."
        exit 1
    }
    Write-Host "[OK] Integrite de l'archive validee avec succes." -ForegroundColor Green
} else {
    if ($latestDump.Length -lt 1024) {
        Send-Alert "L'archive $dumpName semble corrompue ou vide (< 1 Ko)."
        exit 1
    }
    Write-Host "[OK] Archive non vide validee ($sizeMb Mo)." -ForegroundColor Green
}

# Enregistrement etat JSON
$state = @{
    checked_at = $now
    is_valid = $true
    latest_file = $dumpFullName
    size_mb = $sizeMb
    last_backup_timestamp = $fileMtimeUnix
    age_seconds = $ageSeconds
    age_hours = $ageHours
}
$stateFile = Join-Path $BackupDir "backup_state.json"
$state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding utf8

Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "SUCCES : Sauvegarde conforme, recente ($ageHours h < $MaxAgeHours h) et integre." -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
exit 0
