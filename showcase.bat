@echo off
title MedBuddy 10-Step Clinical Verification & Showcase
color 0A
echo ========================================================
echo   Launching MedBuddy Step-by-Step Clinical Showcase...
echo ========================================================
echo.
cd /d "%~dp0"

python showcase_demo.py

echo.
echo ========================================================
echo Press any key to exit the showcase...
echo ========================================================
pause > nul
