@echo off
title AWS Smart Cost Optimizer - Easy Starter
cls
echo ======================================================================
echo      ☁️  AWS Smart Cost Optimizer - One-Click Suite ☁️
echo ======================================================================
echo.

:: 1. Check for .env file
if not exist .env (
    echo [⚠️ WARNING] .env file not found! 
    echo Creating one from .env.example...
    copy .env.example .env
    echo [!] Please open .env and add your AWS credentials before running.
    pause
    exit /b
)

echo [☁️] Cloud AI (Groq LLaMA 3) is enabled via your API Key.

:: 2. Run Initial Scan
echo [🔍] Running initial AWS resource waste scan...
python main.py --scan

echo.

:: 3. Run Dashboard
echo [🖥️] Starting the Web Dashboard...
echo [🌐] Your browser will open shortly at http://127.0.0.1:5000
echo [!] Keep this window open to keep the dashboard alive.

:: Give the server a moment to spin up, then launch browser
start "" "http://127.0.0.1:5000"
python main.py --dashboard

pause
