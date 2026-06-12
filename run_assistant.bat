@echo off
title ALPHA Typing Assistant
cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Check Python availability
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

:: Install dependencies if missing
python -c "import pynput" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install --quiet pynput keyboard
)

cls
echo Starting ALPHA Typing Assistant...
echo  - Type anywhere, suggestions appear automatically
echo  - Close console to stop
echo.
python "alpha_assistant.py"

if errorlevel 1 (
    echo.
    echo [Script exited with error.]
    pause
)
