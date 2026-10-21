@echo off
REM =====================================================================
REM ALPHA Typing Assistant - launcher
REM =====================================================================
cd /d "%~dp0"

REM --- Check that the interpreter exists ----------------------------------
python --version >nul 2>nul
if errorlevel 1 (
    echo [ALPHA] Python was not found on PATH.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         and make sure "Add python.exe to PATH" is checked.
    pause
    exit /b 1
)

REM --- Warn about missing dependencies ------------------------------------
python -c "import pynput" >nul 2>nul
if errorlevel 1 (
    echo [ALPHA] Missing dependency: pynput
    echo         Run: pip install -r requirements.txt
    pause
    exit /b 1
)

python -c "import pyperclip" >nul 2>nul
if errorlevel 1 (
    echo [ALPHA] Missing dependency: pyperclip
    echo         Run: pip install -r requirements.txt
    echo         (ALPHA still works without it, but the clipboard fallback
    echo          for text insertion will be unavailable.)
)

echo [ALPHA] Starting...
python alpha_assistant.py
pause
