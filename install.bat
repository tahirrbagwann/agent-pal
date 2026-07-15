@echo off
title Agent Pal - Installer
echo ==============================================
echo Installing Agent Pal...
echo ==============================================
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python and try again.
    pause
    exit /b 1
)

:: Install package in editable mode
echo [1/3] Installing dependencies and package...
pip install -e .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install package. Make sure pip is updated.
    pause
    exit /b 1
)

:: Create windowless startup VBScript
echo [2/3] Setting up windowless background runner...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_PATH=%STARTUP_FOLDER%\agent-pal-startup.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.Run "pythonw.exe -m agent_pal", 0, False >> "%VBS_PATH%"

echo [3/3] Created startup script at:
echo %VBS_PATH%
echo.
echo ==============================================
echo Installation Complete!
echo.
echo Agent Pal will now start silently in the background on Windows startup.
echo To run it immediately in the background, type:
echo   pythonw.exe -m agent_pal
echo.
echo If you prefer single-session mode (auto-exit when terminal closes), run:
echo   pythonw.exe -m agent_pal --exit-when-idle
echo ==============================================
pause
