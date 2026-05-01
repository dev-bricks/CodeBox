@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)
echo Baue CodeBox.exe...
python -m PyInstaller --noconfirm --clean --windowed --onefile --name CodeBox --icon CodeBox.ico main.py
if errorlevel 1 pause
