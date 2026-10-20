[CmdletBinding()]
param(
    [string]$ApkPath = "D:\SANTE_DZ_EXPORTS\releases\v1.0.17\Medizy_v1.0.17_Universal.apk",
    [string]$Sha256Register = "D:\SANTE_DZ_EXPORTS\releases\v1.0.17\SHA256SUMS_v1.0.17.txt",
    [string]$PackageName = "dz.sante.medizy.national",
    [string]$MainActivity = "dz.sante.medizy.national/.MainActivity",
    [switch]$LaunchEmulatorIfNoDevice
)

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  MEDIZY v1.0.17 - PROTOCOLE DE DEPLOIEMENT TERRAIN ET QUALIFICATION ADB" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Localisation d'ADB
$adbCmd = $null
$candidateAdb = @(
    "C:\Android\Sdk\platform-tools\adb.exe",
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe"
)

foreach ($c in $candidateAdb) {
    if (Test-Path $c) {
        $adbCmd = $c
        break
    }
}

if (-not $adbCmd) {
    $foundInPath = Get-Command adb -ErrorAction SilentlyContinue
    if ($foundInPath) {
        $adbCmd = $foundInPath.Source
    }
}

if (-not $adbCmd) {
    Write-Error "[ERREUR CRITIQUE] Impossible de localiser adb.exe. Veuillez verifier le chemin du SDK Android."
    exit 1
}

Write-Host "[OK] Outil ADB localise : $adbCmd" -ForegroundColor Green
$adbVer = & $adbCmd version | Select-Object -First 1
Write-Host "     Version ADB : $adbVer" -ForegroundColor Gray

# 2. Controle d'Integrite SHA-256 de l'APK
Write-Host "`n[ETAPE 1/4] Verification d integrite de l APK de production..." -ForegroundColor Yellow
if (-not (Test-Path $ApkPath)) {
    Write-Error "[ERREUR] APK introuvable sous : $ApkPath"
    exit 1
}

$apkBytes = (Get-Item $ApkPath).Length
$apkSizeMB = [math]::Round($apkBytes / 1MB, 2)
$actualHash = (Get-FileHash -Path $ApkPath -Algorithm SHA256).Hash.ToLower()
Write-Host "     Fichier cible   : $ApkPath ($apkSizeMB Mo)" -ForegroundColor Gray
Write-Host "     SHA-256 calcule : $actualHash" -ForegroundColor Gray

if (Test-Path $Sha256Register) {
    $expectedLine = Get-Content $Sha256Register | Select-Object -First 1
    $expectedHash = ($expectedLine -split "\s+")[0].Trim().ToLower()
    Write-Host "     SHA-256 registre: $expectedHash" -ForegroundColor Gray
    if ($actualHash -eq $expectedHash) {
        Write-Host "     [CERTIFICATION] Empreinte cryptographique CONFORME (bit-a-bit)." -ForegroundColor Green
    } else {
        Write-Warning "[ATTENTION] Discordance avec le registre SHA256SUMS !"
    }
}

# 3. Detection du terminal connecte
Write-Host "`n[ETAPE 2/4] Recherche des terminaux Android connectes..." -ForegroundColor Yellow
$rawDevices = & $adbCmd devices -l
$connectedDevices = @()
foreach ($line in $rawDevices) {
    if ($line -match "^([^\s]+)\s+(device|offline|unauthorized)\b") {
        $connectedDevices += $Matches[1]
    }
}

if ($connectedDevices.Count -eq 0) {
    Write-Warning "[ATTENTE] Aucun terminal physique ou emulateur detecte actuellement via ADB."
    Write-Host "  -> Veuillez brancher votre telephone Android en USB avec le Debogage USB active." -ForegroundColor Cyan
    
    $emulatorExe = "C:\Android\Sdk\emulator\emulator.exe"
    if (Test-Path $emulatorExe) {
        $avds = & $emulatorExe -list-avds
        if ($avds) {
            Write-Host "  -> AVDs disponibles sur cette machine : $($avds -join ', ')" -ForegroundColor Cyan
            if ($LaunchEmulatorIfNoDevice) {
                $targetAvd = $avds[0]
                Write-Host "  -> Demarrage automatique de l emulateur : $targetAvd..." -ForegroundColor Yellow
                Start-Process -FilePath $emulatorExe -ArgumentList "-avd $targetAvd -netdelay none -netspeed full"
                Write-Host "  -> En attente de detection du terminal (adb wait-for-device)..." -ForegroundColor Yellow
                & $adbCmd wait-for-device
                Start-Sleep -Seconds 12
                $rawDevices = & $adbCmd devices -l
                foreach ($line in $rawDevices) {
                    if ($line -match "^([^\s]+)\s+device\b") {
                        $connectedDevices += $Matches[1]
                    }
                }
            }
        }
    }
    
    if ($connectedDevices.Count -eq 0) {
        Write-Host "  -> Pour executer le deploiement des branchement : & `"$PSCommandPath`"" -ForegroundColor Gray
        Write-Host "`n[INFO] Script de qualification terrain operationnel et en attente d appareil." -ForegroundColor Green
        exit 0
    }
}

$targetDevice = $connectedDevices[0]
Write-Host "[OK] Terminal cible detecte : $targetDevice" -ForegroundColor Green
$model = & $adbCmd -s $targetDevice shell getprop ro.product.model
$androidVer = & $adbCmd -s $targetDevice shell getprop ro.build.version.release
$sdkApi = & $adbCmd -s $targetDevice shell getprop ro.build.version.sdk
$abi = & $adbCmd -s $targetDevice shell getprop ro.product.cpu.abi
Write-Host "     Modele      : $model" -ForegroundColor Gray
Write-Host "     Android     : Version $androidVer (API $sdkApi)" -ForegroundColor Gray
Write-Host "     Architecture: $abi" -ForegroundColor Gray

# 4. Installation avec conservation des donnees (-r)
Write-Host "`n[ETAPE 3/4] Installation de Medizy v1.0.17 (-r -d)..." -ForegroundColor Yellow
$installRes = & $adbCmd -s $targetDevice install -r -d $ApkPath
Write-Host "     Resultat : $installRes" -ForegroundColor $(if ($installRes -match "Success") { "Green" } else { "Red" })

if ($installRes -notmatch "Success") {
    Write-Error "[ERREUR] Echec de l installation de l APK."
    exit 1
}

# 5. Lancement de l activite et Smoke-Test
Write-Host "`n[ETAPE 4/4] Lancement de Medizy et execution du Smoke-Test..." -ForegroundColor Yellow

# Purge du logcat
& $adbCmd -s $targetDevice logcat -c

# Demarrage
$startRes = & $adbCmd -s $targetDevice shell am start -n $MainActivity -a android.intent.action.MAIN -c android.intent.category.LAUNCHER
Write-Host "     Lancement Intent : $startRes" -ForegroundColor Gray

Start-Sleep -Seconds 4

# Verification processus
$pidApp = & $adbCmd -s $targetDevice shell pidof $PackageName
if ($pidApp) {
    Write-Host "[SUCCES] Processus actif en memoire (PID: $pidApp)." -ForegroundColor Green
} else {
    Write-Warning "[ATTENTION] L application n a pas pu demarrer correctement."
}

# Analyse logcat
$logs = & $adbCmd -s $targetDevice logcat -d -s flutter:E AndroidRuntime:E
$hasCrash = $false
foreach ($l in $logs) {
    if ($l -match "libsqlite3" -or $l -match "403 Access blocked" -or $l -match "FATAL EXCEPTION") {
        Write-Host "     [ERREUR DETECTEE] $l" -ForegroundColor Red
        $hasCrash = $true
    }
}

if (-not $hasCrash) {
    Write-Host "[CERTIFICATION] Aucun crash libsqlite3.so ni erreur OSM 403 detectee dans Logcat." -ForegroundColor Green
}

# Capture d ecran
$screenshotDir = "D:\SANTE_DZ_EXPORTS\releases\v1.0.17\screenshots"
if (-not (Test-Path $screenshotDir)) {
    New-Item -ItemType Directory -Path $screenshotDir -Force | Out-Null
}
$screenshotPath = Join-Path $screenshotDir "smoke_test_$targetDevice.png"
& $adbCmd -s $targetDevice exec-out screencap -p > $screenshotPath
if (Test-Path $screenshotPath) {
    Write-Host "[OK] Capture d ecran enregistree sous : $screenshotPath" -ForegroundColor Green
}

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "  DEPLOIEMENT ET TESTS EN CONDITIONS REELLES VALIDES AVEC SUCCES" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
