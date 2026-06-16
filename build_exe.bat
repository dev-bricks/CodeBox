@echo off
chcp 65001 >nul
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)
set "BUILD_ROOT=C:\_Local_DEV\codex_build\codebox"
set "WORK_DIR=%BUILD_ROOT%\work"
set "DIST_DIR=C:\_Local_DEV\codex_build\codebox\dist"
if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"
echo Baue CodeBox.exe...
python -m PyInstaller --noconfirm --clean --workpath "%WORK_DIR%" --distpath "%DIST_DIR%" CodeBox.spec
if errorlevel 1 pause
