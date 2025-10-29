@echo off
REM CryptoBoy One-Time Status Check
REM VoidCat RDC - Quick Performance Snapshot

TITLE CryptoBoy Status Check

echo.
echo ================================================================================
echo   CRYPTOBOY QUICK STATUS CHECK
echo ================================================================================
echo.

REM Enable ANSI colors
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Sync database
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1

REM Show status once
python scripts/monitor_trading.py --once

echo.
pause
