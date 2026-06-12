@echo off
title ALPHA - Intelligent Typing Assistant
cd /d "%~dp0"

:: Use the known working Python path
set PYTHON=C:\Users\Abdul Moiz Ansari\AppData\Local\Programs\Python\Python314\python.exe

:: Verify Python exists at this path
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

:: Check and install dependencies
"%PYTHON%" -c "import pynput, keyboard" 2>nul
if errorlevel 1 (
    echo Installing required dependencies (pynput, keyboard)...
    "%PYTHON%" -m pip install --quiet pynput keyboard
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
echo  - Type in NOTEPAD or CHROME, not this window.
echo  - Close this console window to stop.
echo =============================================================
echo.

"%PYTHON%" "alpha_assistant.py"

if errorlevel 1 (
    echo.
    echo [Script exited with error. Check traceback above.]
    pause
) else (
    echo.
    echo Assistant stopped. Press any key to exit.
    pause >nul
)
