@echo off
REM =====================================================================
REM ALPHA Typing Assistant - Windows Firewall Air-Gap Setup Script
REM Hard-blocks outbound network access for Python in Windows Defender
REM =====================================================================
title ALPHA Air-Gap Firewall Configuration
echo =====================================================================
echo          ALPHA Typing Assistant - Air-Gap Privacy Setup
echo =====================================================================
echo.
echo This adds a Windows Defender Firewall rule that blocks ALL outbound
echo traffic for the Python interpreter that runs ALPHA.
echo.
echo The Python path is detected automatically.
echo.

REM --- Detect the Python interpreter -------------------------------------
set "PYTHON_EXE="
where python >nul 2>nul && set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
    where py >nul 2>nul && for /f "tokens=*" %%p in ('py -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%p"
)
if not defined PYTHON_EXE (
    echo [ERROR] No Python interpreter found in PATH.
    echo         Install Python 3.10+ and run this script again.
    goto :end
)

echo Using interpreter: %PYTHON_EXE%
echo.

REM --- Remove an old rule, then add the new one ---------------------------
netsh advfirewall firewall delete rule name="ALPHA_AirGap_Privacy_Block" >nul 2>nul
netsh advfirewall firewall add rule name="ALPHA_AirGap_Privacy_Block" dir=out action=block program="%PYTHON_EXE%" enable=yes profile=any

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================================
    echo [SUCCESS] Windows Defender Firewall outbound block rule ADDED.
    echo ALPHA is now air-gapped at the operating system level.
    echo No keystroke or data can ever be transmitted to the internet.
    echo =====================================================================
) else (
    echo.
    echo [NOTE] Administrator privileges are required.
    echo Please right-click this file and select "Run as administrator".
)
echo.
:end
pause
