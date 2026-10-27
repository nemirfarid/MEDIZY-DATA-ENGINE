@echo off
setlocal EnableDelayedExpansion
title MEDIZY v1.4.0 - Installateur Mobile Automatique

echo ===============================================================================
echo     MEDIZY - DEPLOIEMENT RAPIDE SUR SMARTPHONE ANDROID (TERRAIN)
echo     Version : v1.4.0 National (58 Wilayas - DCI, Generiques & WhatsApp Express)
echo ===============================================================================
echo.

set "APK_PATH=%~dp0dist\Medizy-v1.4.0-National-Release.apk"

if not exist "%APK_PATH%" (
    echo [ERREUR] Le binaire d'installation est introuvable :
    echo         "%APK_PATH%"
    echo.
    echo Veuillez vous assurer que le dossier 'dist' contient l'APK de release.
    pause
    exit /b 1
)

set "ADB_BIN="

where adb.exe >nul 2>nul
if %errorlevel% equ 0 (
    set "ADB_BIN=adb.exe"
    goto ADB_FOUND
)

if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    set "ADB_BIN=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
    goto ADB_FOUND
)

if defined ANDROID_HOME (
    if exist "%ANDROID_HOME%\platform-tools\adb.exe" (
        set "ADB_BIN=%ANDROID_HOME%\platform-tools\adb.exe"
        goto ADB_FOUND
    )
)

if defined ANDROID_SDK_ROOT (
    if exist "%ANDROID_SDK_ROOT%\platform-tools\adb.exe" (
        set "ADB_BIN=%ANDROID_SDK_ROOT%\platform-tools\adb.exe"
        goto ADB_FOUND
    )
)

echo [ERREUR] Android Debug Bridge (ADB) n'a pas ete detecte automatiquement.
echo.
echo Veuillez verifier que :
echo   1. Android SDK Platform-Tools est installe sur cette machine.
echo   2. Ou ajoutez le dossier 'platform-tools' a votre variable PATH.
echo.
pause
exit /b 1

:ADB_FOUND
echo [OK] Outil ADB detecte :
echo      "!ADB_BIN!"
echo.

echo ===============================================================================
echo [ETAPE 1/2] En attente de connexion de votre smartphone Android...
echo.
echo Instructions :
echo   - Reliez le smartphone a l'ordinateur par cable USB
echo   - Activez le Debogage USB dans les options de developpement du telephone
echo   - Validez l'autorisation 'Toujours autoriser cet ordinateur' sur l'ecran
echo ===============================================================================
echo.

"!ADB_BIN!" wait-for-device

echo.
echo [OK] Smartphone Android detecte avec succes !
echo.
"!ADB_BIN!" devices -l
echo.

echo ===============================================================================
echo [ETAPE 2/2] Installation de MEDIZY en cours... (26.2 Mo)
echo             Veuillez patienter pendant le transfert et l'ecriture...
echo ===============================================================================
echo.

"!ADB_BIN!" install -r "%APK_PATH%"

if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] L'installation a echoue.
    echo Verifiez que le smartphone est deverrouille et qu'aucune invite
    echo de securite ('Verifier via USB') ne bloque l'installation.
    echo.
    pause
    exit /b %errorlevel%
)

echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host '===============================================================================' -ForegroundColor Cyan; Write-Host '  FELICITATIONS ! INSTALLATION TERMINEE AVEC SUCCES SUR LE SMARTPHONE !' -ForegroundColor Green; Write-Host '  MEDIZY v1.4.0 National est pret a fonctionner 100% hors-ligne.' -ForegroundColor White; Write-Host '  -----------------------------------------------------------------------------' -ForegroundColor DarkGray; Write-Host '  ! مبروك ! تم تثبيت تطبيق ميديزي (MEDIZY) بنجاح على هاتفك المحمول' -ForegroundColor Yellow; Write-Host '  دليل الصحة الوطني الجزائري (58 ولاية) جاهز للاستخدام الكامل بدون إنترنت' -ForegroundColor Cyan; Write-Host '===============================================================================' -ForegroundColor Cyan"
echo.

set /p LAUNCH="Voulez-vous lancer l'application sur le telephone des maintenant ? (O/N) : "
if /i "!LAUNCH!"=="O" (
    "!ADB_BIN!" shell monkey -p dz.sante.medizy.national -c android.intent.category.LAUNCHER 1 >nul 2>nul
    echo [OK] Application MEDIZY lancee avec succes sur le smartphone.
)

echo.
echo Installation terminee. Appuyez sur une touche pour quitter.
pause >nul
exit /b 0
