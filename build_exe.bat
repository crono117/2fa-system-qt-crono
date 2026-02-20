@echo off
REM ==============================================================
REM  2FA Merchant Verification System (PySide2)
REM  Windows executable build script
REM
REM  Requirements:
REM    - Python 3.10 or 3.11 (from python.org)
REM    - Internet access (downloads packages on first run)
REM
REM  Usage:
REM    Double-click build_exe.bat  OR  run from Command Prompt
REM
REM  Output:
REM    dist\2FA_System_Distribution\
REM      2FA_System.exe   <- distribute this
REM      config.ini       <- edit server URL before distributing
REM ==============================================================

echo.
echo ==============================================
echo   2FA System (Qt) - Building Windows EXE
echo ==============================================
echo.

cd /d "%~dp0"

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download Python 3.10+ from https://python.org and re-run.
    pause
    exit /b 1
)
python --version

REM --- Virtual environment ---
if not exist "venv_build" (
    echo Creating virtual environment...
    python -m venv venv_build
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv_build\Scripts\activate.bat

REM --- Dependencies ---
echo.
echo Installing / updating dependencies...
python -m pip install --upgrade pip --quiet
pip install PySide2>=5.15.0 requests cryptography keyring loguru --quiet
pip install pyinstaller --quiet

REM --- Clean ---
echo Cleaning previous build artefacts...
if exist "build"  rmdir /s /q build
if exist "dist"   rmdir /s /q dist

REM --- Build ---
echo.
echo Running PyInstaller (this takes a few minutes)...
echo.
pyinstaller 2fa_system_qt.spec --clean

REM --- Result ---
if exist "dist\2FA_System.exe" (
    echo.
    echo ==============================================
    echo   BUILD SUCCESSFUL!
    echo ==============================================
    echo.

    REM Create distribution folder
    if not exist "dist\2FA_System_Distribution" mkdir "dist\2FA_System_Distribution"
    copy /y "dist\2FA_System.exe" "dist\2FA_System_Distribution\" >nul
    copy /y "config.ini"          "dist\2FA_System_Distribution\" >nul

    echo Distribution package ready:
    echo   dist\2FA_System_Distribution\2FA_System.exe
    echo   dist\2FA_System_Distribution\config.ini
    echo.
    echo IMPORTANT — before distributing, edit config.ini:
    echo   Production server:  api_base_url = http://10.5.96.4:8000/api
    echo   Local testing:      api_base_url = http://127.0.0.1:8000/api
    echo.
) else (
    echo.
    echo BUILD FAILED — check the output above for errors.
    pause
    exit /b 1
)

pause
