@echo off
title Google Maps Lead Finder Pro
cd /d "%~dp0"

echo ========================================================
echo    Starting Google Maps Lead Finder Pro...
echo ========================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .venv!
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

.venv\Scripts\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo Server stopped with error code %errorlevel%.
    pause
)
