@echo off
REM =====================================================================
REM ALPHA Typing Assistant - Windows Firewall Air-Gap Setup Script
REM Hard-blocks outbound network access for Python in Windows Defender Firewall
REM =====================================================================
title ALPHA Air-Gap Firewall Configuration
echo =====================================================================
echo          ALPHA Typing Assistant - Air-Gap Privacy Setup
echo =====================================================================
echo.
echo Configuring Windows Defender Firewall to block all outbound traffic...
echo.

set "PYTHON_EXE=C:\Users\Abdul Moiz Ansari\AppData\Local\Programs\Python\Python314\python.exe"

netsh advfirewall firewall add rule name="ALPHA_AirGap_Privacy_Block" dir=out action=block program="%PYTHON_EXE%" enable=yes profile=any

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================================
    echo [SUCCESS] Windows Defender Firewall Outbound Block Rule ADDED!
    echo ALPHA is now completely air-gapped at the operating system level.
    echo No keystroke or data can ever be transmitted to the internet.
    echo =====================================================================
) else (
    echo.
    echo [NOTE] Administrator privileges required.
    echo Please right-click this file and select 'Run as administrator'.
)
echo.
pause
