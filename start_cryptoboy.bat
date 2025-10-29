@echo off
TITLE CryptoBoy Trading System - VoidCat RDC
COLOR 0A

REM ============================================================================
REM CryptoBoy Complete Trading System Launcher
REM VoidCat RDC - Excellence in Automated Trading
REM ============================================================================

echo.
echo ================================================================================
echo                   CRYPTOBOY TRADING SYSTEM - VOIDCAT RDC
echo ================================================================================
echo.

REM Enable ANSI colors for better display
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Navigate to project directory
cd /d "%~dp0"
echo [+] Project Directory: %CD%
echo.

REM ============================================================================
REM STEP 1: Check Docker Status
REM ============================================================================
echo [STEP 1/5] Checking Docker...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running! Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is running
echo.

REM ============================================================================
REM STEP 2: Start Trading Bot Container
REM ============================================================================
echo [STEP 2/5] Starting Trading Bot...
docker ps | findstr "trading-bot-app" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Trading bot is already running
) else (
    docker ps -a | findstr "trading-bot-app" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [*] Starting existing container...
        docker start trading-bot-app >nul 2>&1
    ) else (
        echo [*] Creating new trading bot container...
        docker-compose up -d
    )
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to start trading bot!
        pause
        exit /b 1
    )
    echo [OK] Trading bot started successfully
)
echo.

REM Wait for bot to initialize
echo [*] Waiting for bot initialization...
timeout /t 5 /nobreak >nul
echo.

REM ============================================================================
REM STEP 3: Check Bot Health
REM ============================================================================
echo [STEP 3/5] Checking Bot Health...
docker logs trading-bot-app --tail 20 | findstr /C:"RUNNING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Bot is running and healthy
) else (
    echo [WARNING] Bot may still be starting up...
)
echo.

REM ============================================================================
REM STEP 4: Display System Status
REM ============================================================================
echo [STEP 4/5] System Status Check...
echo.
echo --- Trading Bot Status ---
docker ps --filter "name=trading-bot-app" --format "  Container: {{.Names}}\n  Status: {{.Status}}\n  Ports: {{.Ports}}"
echo.

REM Get latest sentiment data age
if exist "data\sentiment_signals.csv" (
    echo [OK] Sentiment data file found
    for %%F in ("data\sentiment_signals.csv") do echo   Last updated: %%~tF
) else (
    echo [WARNING] Sentiment data file not found - run data pipeline first
)
echo.

REM ============================================================================
REM STEP 5: Launch Monitoring Dashboard
REM ============================================================================
echo [STEP 5/5] Launching Trading Monitor...
echo.
echo ================================================================================
echo.
echo [*] Starting live trading monitor in 3 seconds...
echo [*] Press Ctrl+C to stop monitoring
echo.
echo     Monitor Features:
echo       - Real-time balance tracking
echo       - Live trade notifications
echo       - Performance statistics
echo       - Sentiment headlines
echo       - Auto-refresh every 15 seconds
echo.
echo ================================================================================
echo.

timeout /t 3 /nobreak >nul

REM Sync database from container
echo [*] Syncing database...
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1

REM Launch monitor in live mode
python scripts/monitor_trading.py --interval 15

REM ============================================================================
REM Cleanup on Exit
REM ============================================================================
echo.
echo.
echo ================================================================================
echo Monitor stopped. Trading bot is still running in background.
echo ================================================================================
echo.
echo To manage the bot:
echo   - View logs:     docker logs trading-bot-app --tail 50
echo   - Restart bot:   docker restart trading-bot-app
echo   - Stop bot:      docker stop trading-bot-app
echo   - Start monitor: start_monitor.bat
echo.
echo VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
pause
