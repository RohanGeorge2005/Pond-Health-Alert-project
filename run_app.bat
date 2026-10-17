@echo off
title Pond Health Alert - Launcher
color 0A

echo ===================================================
echo     Starting Pond Health Alert (PS 1.1)
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting FastAPI Backend on port 8000...
start "Pond Health API" cmd /k "python -m uvicorn apps.api.main:app --reload --port 8000 --host 0.0.0.0"

echo [2/3] Starting Vite Web Dashboard on port 5173...
cd apps\web
start "Pond Health Dashboard" cmd /k "npm run dev"

echo.
echo [3/3] Waiting 4 seconds for servers to initialize...
timeout /t 4 /nobreak >nul

echo Opening dashboard in your default browser...
start http://localhost:5173

echo.
echo ===================================================
echo   System running!
echo   - Web Dashboard: http://localhost:5173
echo   - Backend API Docs: http://localhost:8000/docs
echo ===================================================
pause
