@echo off
title ALPHA - Intelligent Typing Assistant

:: Auto-elevate to Administrator for global hooks
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges for global hooks...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: Check if Python is installed
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

:: Install only needed dependencies (no pyautogui/pyperclip)
python -c "import pynput, keyboard" 2>nul
if errorlevel 1 (
    echo Installing required dependencies (pynput, keyboard)...
    python -m pip install --quiet pynput keyboard
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
)

cls
echo =============================================================
echo   ALPHA Typing Assistant v3.5 FINAL  
echo =============================================================
echo.
echo  Status: Running as Administrator
echo  Hotkeys: Ctrl+Alt+X (Toggle), Ctrl+Alt+S (Summary)
echo.
echo  - Type anywhere, suggestions appear automatically.
echo  - Close this console window to stop.
echo =============================================================
echo.

python "alpha_assistant.py"

if errorlevel 1 (
    echo.
    echo [Script exited with error. Check traceback above.]
    pause
)
