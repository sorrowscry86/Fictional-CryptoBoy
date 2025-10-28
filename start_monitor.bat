@echo off
REM CryptoBoy Live Trading Monitor Launcher
REM VoidCat RDC - Trading Performance Monitor
REM
REM This script launches the real-time trading monitor with color support

TITLE CryptoBoy Trading Monitor - VoidCat RDC

echo.
echo ================================================================================
echo   CRYPTOBOY LIVE TRADING MONITOR
echo   VoidCat RDC - Real-Time Performance Tracking
echo ================================================================================
echo.
echo   Starting monitor...
echo   Press Ctrl+C to exit
echo.
echo ================================================================================
echo.

REM Enable ANSI color support in Windows console
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Copy latest database from Docker container
echo [*] Syncing database from Docker container...
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Could not sync database. Monitor will show last cached data.
    echo.
)

REM Launch the monitor
python scripts/monitor_trading.py --interval 15

REM Cleanup message on exit
echo.
echo ================================================================================
echo   Monitor stopped
echo ================================================================================
echo.
pause
