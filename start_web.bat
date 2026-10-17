@echo off
title Pond Health Alert - Setup and Run
color 0B

echo ===================================================
echo     Setting up & Starting Pond Health Alert
echo ===================================================
echo.

cd /d "%~dp0apps\web"

if not exist node_modules (
    echo [INFO] Installing web dependencies (one-time setup)...
    call npm install --legacy-peer-deps
)

echo.
echo [INFO] Starting Vite development server...
call npm run dev

pause
