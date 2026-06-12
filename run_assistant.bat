@echo off
title ALPHA - Intelligent Typing Assistant
cd /d "%~dp0"

:: Detect Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python and add to PATH.
    pause
    exit /b 1
)

:: Check dependencies
python -c "import pynput" 2>nul
if %errorlevel% neq 0 (
    echo Installing pynput...
    python -m pip install pynput
)

python -c "import keyboard" 2>nul
if %errorlevel% neq 0 (
    echo Installing keyboard...
    python -m pip install keyboard
)

cls
echo ============================================================
echo   ALPHA Typing Assistant v3.5
echo   English + Roman Urdu
echo ============================================================
echo.
echo   HOW TO USE:
echo   1. This window stays open (control panel)
echo   2. Switch to Notepad, Chrome, WhatsApp, etc.
echo   3. Start typing - suggestions appear automatically
echo.
echo   HOTKEYS:
echo   Ctrl+Alt+X  = Toggle ON/OFF
echo   Ctrl+Alt+S  = Show session summary
echo.
echo   To STOP: Close this console window.
echo ============================================================
echo.

python alpha_assistant.py

echo.
echo [Assistant stopped]
pause
