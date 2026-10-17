<#
.SYNOPSIS
    Script de gestion du service d'arrière-plan Windows Santé DZ Medizy.
.DESCRIPTION
    Lance, arrête ou inspecte l'état du serveur API REST en tâche de fond discrète (sans fenêtre UI),
    avec redirection automatique des journaux vers D:\SANTE_DZ_EXPORTS\logs\api_service.log.
.PARAMETER Action
    start, stop, status, restart (défaut : start)
.PARAMETER Port
    Port d'écoute (défaut : 8000)
.PARAMETER HostAddress
    Adresse d'écoute (défaut : 0.0.0.0)
#>

param (
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start",
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

# Définition des chemins d'exécution et de stockage
$WorkspaceDir = "C:\SANTE_DZ_SCRAPER"
$PythonExe    = Join-Path $WorkspaceDir ".venv\Scripts\python.exe"
$ServerScript = Join-Path $WorkspaceDir "api_server.py"

$LogDir       = "D:\SANTE_DZ_EXPORTS\logs"
$LogFile      = Join-Path $LogDir "api_service.log"
$PidFile      = Join-Path $LogDir "api_service.pid"

# Création du dossier de logs sécurisé sur D:\
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Get-RunningProcess {
    if (Test-Path $PidFile) {
        $savedPid = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($savedPid -match '^\d+$') {
            $proc = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
            if ($proc) {
                return $proc
            }
        }
    }
    return $null
}

function Write-ServiceLog([string]$message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $entry = "[$timestamp] $message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

switch ($Action) {
    "start" {
        $existing = Get-RunningProcess
        if ($existing) {
            Write-Host "[ATTENTION] Le service Santé DZ Medizy est déjà en cours d'exécution (PID: $($existing.Id))." -ForegroundColor Yellow
            exit 0
        }

        if (-not (Test-Path $PythonExe)) {
            Write-Error "Interpréteur Python introuvable : $PythonExe"
            exit 1
        }
        if (-not (Test-Path $ServerScript)) {
            Write-Error "Script serveur introuvable : $ServerScript"
            exit 1
        }

        Write-ServiceLog "Démarrage du service d'arrière-plan Santé DZ Medizy..."

        $argList = @(
            "`"$ServerScript`"",
            "--host", $HostAddress,
            "--port", "$Port"
        )

        $proc = Start-Process -FilePath $PythonExe `
                              -ArgumentList $argList `
                              -WorkingDirectory $WorkspaceDir `
                              -WindowStyle Hidden `
                              -RedirectStandardOutput $LogFile `
                              -RedirectStandardError $LogFile `
                              -PassThru

        if ($proc -and -not $proc.HasExited) {
            $proc.Id | Out-File -FilePath $PidFile -Encoding ascii -Force
            Start-Sleep -Seconds 2
            if (-not $proc.HasExited) {
                Write-Host "[SUCCÈS] Service démarré en arrière-plan avec succès !" -ForegroundColor Green
                Write-Host "  * PID : $($proc.Id)"
                Write-Host "  * Écoute : http://${HostAddress}:${Port}"
                Write-Host "  * Fichier journal : $LogFile"
                Write-ServiceLog "Service actif avec le PID $($proc.Id)."
            } else {
                Write-Error "Le processus a quitté prématurément. Consultez $LogFile pour les détails."
                exit 1
            }
        } else {
            Write-Error "Échec lors de l'initialisation du processus d'arrière-plan."
            exit 1
        }
    }

    "stop" {
        $proc = Get-RunningProcess
        if ($proc) {
            Write-ServiceLog "Arrêt du service Santé DZ Medizy (PID: $($proc.Id))..."
            Stop-Process -Id $proc.Id -Force
            Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
            Write-Host "[SUCCÈS] Service arrêté avec succès." -ForegroundColor Green
            Write-ServiceLog "Service arrêté."
        } else {
            Write-Host "[INFO] Aucun service Santé DZ Medizy en cours d'exécution." -ForegroundColor Cyan
            if (Test-Path $PidFile) {
                Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
            }
        }
    }

    "status" {
        $proc = Get-RunningProcess
        if ($proc) {
            Write-Host "[ACTIF] Le service Santé DZ Medizy est en cours d'exécution." -ForegroundColor Green
            Write-Host "  * PID : $($proc.Id)"
            Write-Host "  * Mémoire : $([math]::Round($proc.WorkingSet64 / 1MB, 2)) Mo"
            Write-Host "  * Logs : $LogFile"
            
            # Test du healthcheck HTTP local
            try {
                $response = Invoke-RestMethod -Uri "http://127.0.0.1:${Port}/api/v1/health" -TimeoutSec 3
                Write-Host "  * Healthcheck HTTP : OK (Établissements: $($response.metrics.total_facilities))" -ForegroundColor Green
            } catch {
                Write-Host "  * Healthcheck HTTP : Erreur de communication ($($_.Exception.Message))" -ForegroundColor Red
            }
        } else {
            Write-Host "[INACTIF] Le service n'est pas en cours d'exécution." -ForegroundColor Yellow
        }
    }

    "restart" {
        & $PSCommandPath -Action stop
        Start-Sleep -Seconds 1
        & $PSCommandPath -Action start -HostAddress $HostAddress -Port $Port
    }
}
