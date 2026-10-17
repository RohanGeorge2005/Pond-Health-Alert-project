@echo off
title Pond Health Alert - Automated Test Runner
color 0B

echo ===================================================
echo     Running Full Pond Health Alert Test Suite
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/2] Running Python Backend Tests (pytest)...
python -m pytest apps/api/tests -v
set BACKEND_EXIT=%ERRORLEVEL%

echo.
echo [2/2] Running Frontend Validation Tests...
cd apps\web
node src\tests\run_tests.js
set FRONTEND_EXIT=%ERRORLEVEL%

echo.
echo ===================================================
if %BACKEND_EXIT% EQU 0 (
    if %FRONTEND_EXIT% EQU 0 (
        color 0A
        echo   ALL TESTS PASSED SUCCESSFULLY!
    ) else (
        color 0C
        echo   BACKEND PASSED, BUT FRONTEND TESTS REPORTED ISSUES.
    )
) else (
    color 0C
    echo   BACKEND TESTS FAILED.
)
echo ===================================================
pause
