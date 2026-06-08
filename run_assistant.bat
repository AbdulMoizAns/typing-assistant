@echo off
title Global Typing Assistant
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

python -c "import pyautogui, pyperclip, pynput" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install --quiet pyautogui pyperclip pynput
    if errorlevel 1 (
        echo [ERROR] Failed to install.
        pause
        exit /b 1
    )
)

cls
echo Starting Global Typing Assistant...
echo  - Type anywhere, suggestions appear automatically
echo  - Close console to stop
echo.
python "alpha_assistant.py"

if errorlevel 1 (
    echo.
    echo [Script exited with error.]
    pause
)
