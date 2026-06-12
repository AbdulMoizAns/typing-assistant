@echo off
title ALPHA - Intelligent Typing Assistant
cd /d "%~dp0"

:: Check if running as Administrator
>nul 2>&1 fltmc
if %errorlevel% neq 0 (
    echo.
    echo  NOT running as Administrator.
    echo  Global hooks may not work in elevated apps (VS Code, CMD, etc.).
    echo  Right-click this file and select "Run as administrator" for full compatibility.
    echo.
    echo  Starting in 3 seconds...
    timeout /t 3 /nobreak >nul
)

:: Check if Python is installed
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

:: Install only needed dependencies
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
>nul 2>&1 fltmc && echo  Status: Running as Administrator || echo  Status: Standard User
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
) else (
    echo.
    echo Assistant stopped. Press any key to exit.
    pause >nul
)
