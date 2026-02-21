@echo off
REM EVAgent Background Sync Service for Windows
REM Batch script to run the sync service as a Windows service

echo Starting EVAgent Background Sync Service...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "background_sync_service.py" (
    echo Error: background_sync_service.py not found
    echo Please run this script from the EVAgent directory
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start the sync service
echo Starting background synchronization...
echo Press Ctrl+C to stop the service
echo.

python background_sync_service.py

echo.
echo EVAgent Background Sync Service stopped
pause
