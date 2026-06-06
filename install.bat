@echo off
echo === Apple Music Playlist Downloader - Installation ===
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe.
    echo Telechargez-le sur https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python detecte

:: Install ffmpeg via winget
echo.
echo Installation de ffmpeg...
winget install --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [INFO] ffmpeg deja installe ou echec - on continue
)
echo [OK] ffmpeg

:: Install Python dependencies
echo.
echo Installation des dependances Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Echec de pip install
    pause
    exit /b 1
)
echo [OK] Dependances Python

:: Install Playwright Chromium
echo.
echo Installation du navigateur Chromium (Playwright)...
python -m playwright install chromium
if errorlevel 1 (
    echo [ERREUR] Echec de playwright install
    pause
    exit /b 1
)
echo [OK] Chromium

echo.
echo === Installation terminee ! ===
echo Pour lancer l'application : double-cliquez sur start.bat
echo                         ou : python app.py
pause
