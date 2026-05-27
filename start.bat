@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "DIST_EXE=dist\CodeBox.exe"
set "RELEASE_EXE=releases\v0.1.0\CodeBox-0.1.0-win64.exe"
if exist "%DIST_EXE%" (
    start "" "%DIST_EXE%"
    exit /b 0
)
if exist "%RELEASE_EXE%" (
    start "" "%RELEASE_EXE%"
    exit /b 0
)
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden und keine EXE vorhanden.
    pause
    exit /b 1
)
python main.py
pause
