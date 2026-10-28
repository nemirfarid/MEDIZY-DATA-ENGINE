<#
.SYNOPSIS
    Script de sauvegarde automatisée PostGIS pour environnement Windows / PowerShell (MEDIZY).
.DESCRIPTION
    Exécute un pg_dump compressé, valide l'intégrité de l'archive avec pg_restore,
    applique une rotation sur 14 jours et consigne les métriques d'audit.
#>

param (
    [string]$PostgresHost = $env:POSTGRES_HOST ?? "localhost",
    [int]$PostgresPort = [int]($env:POSTGRES_PORT ?? 5432),
    [string]$PostgresDb = $env:POSTGRES_DB ?? "medizy_db",
    [string]$PostgresUser = $env:POSTGRES_USER ?? "medizy_user",
    [string]$PostgresPassword = $env:POSTGRES_PASSWORD ?? "medizy_password",
    [string]$BackupDir = $env:BACKUP_DIR ?? "C:\medizy_backups\postgis",
    [int]$RetentionDays = 14,
    [string]$S3Bucket = $env:S3_BUCKET ?? ""
)

$ErrorActionPreference = "Stop"
$env:PGPASSWORD = $PostgresPassword

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFilename = "medizy_postgis_${PostgresDb}_${Timestamp}.dump"
$BackupPath = Join-Path $BackupDir $BackupFilename
$LogFile = Join-Path $BackupDir "backup_execution.log"

function Write-AuditLog([string]$level, [string]$message) {
    $entry = [PSCustomObject]@{
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        level = $level
        message = $message
    }
    $json = $entry | ConvertTo-Json -Compress
    Write-Host "[$level] $message"
    Add-Content -Path $LogFile -Value $json
}

Write-AuditLog "INFO" "Démarrage de la sauvegarde PostGIS pour '$PostgresDb'..."
$StartTime = Get-Date

try {
    # Exécution de pg_dump
    $dumpArgs = @(
        "-h", $PostgresHost,
        "-p", $PostgresPort.ToString(),
        "-U", $PostgresUser,
        "-d", $PostgresDb,
        "-Fc",
        "-Z", "9",
        "--blobs",
        "-f", $BackupPath
    )
    
    $proc = Start-Process -FilePath "pg_dump" -ArgumentList $dumpArgs -Wait -NoNewWindow -PassThru -RedirectStandardError (Join-Path $BackupDir "pg_dump_err.log")
    if ($proc.ExitCode -ne 0) {
        throw "pg_dump a échoué avec le code de sortie $($proc.ExitCode)"
    }

    $fileItem = Get-Item $BackupPath
    $sizeMb = [math]::Round($fileItem.Length / 1MB, 2)
    Write-AuditLog "INFO" "Archive PostGIS générée : $BackupFilename ($sizeMb Mo)."

    # Validation d'intégrité
    $restoreArgs = @("--list", $BackupPath)
    $valProc = Start-Process -FilePath "pg_restore" -ArgumentList $restoreArgs -Wait -NoNewWindow -PassThru -RedirectStandardOutput $null -RedirectStandardError (Join-Path $BackupDir "restore_val_err.log")
    if ($valProc.ExitCode -eq 0) {
        Write-AuditLog "INFO" "Validation d'intégrité RÉUSSIE : L'archive est valide et restaurable."
    } else {
        throw "Archive corrompue détectée par pg_restore."
    }

    # Rotation sur 14 jours
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $purged = 0
    Get-ChildItem -Path $BackupDir -Filter "medizy_postgis_*.dump" | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
        Remove-Item $_.FullName -Force
        $purged++
        Write-AuditLog "INFO" "Ancienne archive purgée : $($_.Name)"
    }

    $duration = [math]::Round(((Get-Date) - $StartTime).TotalSeconds, 2)
    Write-AuditLog "INFO" "Sauvegarde terminée en ${duration}s. Archives purgées : $purged."
}
catch {
    Write-AuditLog "ERROR" "Échec de sauvegarde PostGIS : $_"
    exit 1
}
