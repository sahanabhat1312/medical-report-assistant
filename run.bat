@echo off
title MedBuddy AI Medical Report Assistant
color 0A
echo ========================================================
echo        Starting MedBuddy Medical Assistant MVP...
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] Checking Python environment...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo [2/2] Launching MedBuddy Server...
echo.
echo Application will be available at: http://127.0.0.1:5000
echo (Press Ctrl+C in this window to stop the server)
echo.

start http://127.0.0.1:5000
python app.py

pause
