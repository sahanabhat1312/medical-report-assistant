@echo off
title MedBuddy Automated Verification Test Runner
color 0B
echo ========================================================
echo     Running MedBuddy Automated Verification Suite...
echo ========================================================
echo.
cd /d "%~dp0"

python -m unittest tests/test_verification_suite.py -v
echo.
echo ========================================================
echo Verification complete.
echo ========================================================
pause
