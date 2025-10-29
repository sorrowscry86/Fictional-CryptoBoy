@echo off
TITLE CryptoBoy Trading System - VoidCat RDC
COLOR 0A

REM ============================================================================
REM CryptoBoy Microservice Architecture Launcher
REM VoidCat RDC - Excellence in Automated Trading
REM Architecture: Message-Driven Microservices with RabbitMQ & Redis
REM ============================================================================

echo.
echo ================================================================================
echo                   CRYPTOBOY TRADING SYSTEM - VOIDCAT RDC
echo                    Microservice Architecture - Production Ready
echo ================================================================================
echo.

REM Enable ANSI colors for better display
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Navigate to project directory
cd /d "%~dp0"
echo [+] Project Directory: %CD%
echo.

REM ============================================================================
REM LAUNCH MODE SELECTION
REM ============================================================================
echo Select Launch Mode:
echo   [1] Microservice Architecture (RabbitMQ + Redis + 4 Services)
echo   [2] Legacy Monolithic Mode (Single Container)
echo   [3] Status Check Only
echo.
set /p mode="Enter choice (1-3): "
echo.

if "%mode%"=="3" goto STATUS_CHECK
if "%mode%"=="2" goto LEGACY_MODE
if not "%mode%"=="1" (
    echo [ERROR] Invalid choice. Defaulting to Microservice Mode...
    timeout /t 2 /nobreak >nul
)

REM ============================================================================
REM MICROSERVICE MODE
REM ============================================================================
:MICROSERVICE_MODE
echo ================================================================================
echo   MICROSERVICE ARCHITECTURE MODE
echo ================================================================================
echo.

REM ============================================================================
REM STEP 1: Check Docker Status
REM ============================================================================
echo [STEP 1/7] Checking Docker...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running! Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is running
echo.

REM ============================================================================
REM STEP 2: Environment Check
REM ============================================================================
echo [STEP 2/7] Checking Environment Variables...
if not defined RABBITMQ_USER (
    echo [WARNING] RABBITMQ_USER not set. Using default: admin
    set RABBITMQ_USER=admin
)
if not defined RABBITMQ_PASS (
    echo [WARNING] RABBITMQ_PASS not set. Using default: cryptoboy_secret
    set RABBITMQ_PASS=cryptoboy_secret
)
echo [OK] RabbitMQ credentials configured
echo   User: %RABBITMQ_USER%
echo.

REM ============================================================================
REM STEP 3: Start Infrastructure Services
REM ============================================================================
echo [STEP 3/7] Starting Infrastructure Services...
echo   [*] Starting RabbitMQ (Message Broker)...
docker-compose up -d rabbitmq >nul 2>&1
echo   [*] Starting Redis (Cache Server)...
docker-compose up -d redis >nul 2>&1
echo [OK] Infrastructure services started
echo.
echo [*] Waiting for services to initialize...
timeout /t 8 /nobreak >nul

REM Verify RabbitMQ
echo [*] Verifying RabbitMQ...
docker exec rabbitmq rabbitmqctl status >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] RabbitMQ is healthy
) else (
    echo [WARNING] RabbitMQ may still be initializing
)

REM Verify Redis
echo [*] Verifying Redis...
docker exec redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis is healthy
) else (
    echo [WARNING] Redis may still be initializing
)
echo.

REM ============================================================================
REM STEP 4: Start Microservices
REM ============================================================================
echo [STEP 4/7] Starting Microservices...
echo   [*] Starting Market Data Streamer...
docker-compose up -d market-streamer >nul 2>&1
echo   [*] Starting News Poller...
docker-compose up -d news-poller >nul 2>&1
echo   [*] Starting Sentiment Processor...
docker-compose up -d sentiment-processor >nul 2>&1
echo   [*] Starting Signal Cacher...
docker-compose up -d signal-cacher >nul 2>&1
echo [OK] All microservices started
echo.
echo [*] Waiting for microservices to initialize...
timeout /t 5 /nobreak >nul
echo.

REM ============================================================================
REM STEP 5: Start Trading Bot
REM ============================================================================
echo [STEP 5/7] Starting Trading Bot (Freqtrade)...
docker-compose up -d trading-bot-app >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start trading bot!
    pause
    exit /b 1
)
echo [OK] Trading bot started successfully
echo.
echo [*] Waiting for bot initialization...
timeout /t 5 /nobreak >nul
echo.

REM ============================================================================
REM STEP 6: Health Check All Services
REM ============================================================================
echo [STEP 6/7] System Health Check...
echo.
echo --- Infrastructure Status ---
docker ps --filter "name=rabbitmq" --format "  [+] {{.Names}}: {{.Status}}"
docker ps --filter "name=redis" --format "  [+] {{.Names}}: {{.Status}}"
echo.
echo --- Microservices Status ---
docker ps --filter "name=market-streamer" --format "  [+] {{.Names}}: {{.Status}}"
docker ps --filter "name=news-poller" --format "  [+] {{.Names}}: {{.Status}}"
docker ps --filter "name=sentiment-processor" --format "  [+] {{.Names}}: {{.Status}}"
docker ps --filter "name=signal-cacher" --format "  [+] {{.Names}}: {{.Status}}"
echo.
echo --- Trading Bot Status ---
docker ps --filter "name=trading-bot-app" --format "  [+] {{.Names}}: {{.Status}}"
echo.

REM Check RabbitMQ queues
echo [*] Checking message queues...
docker exec rabbitmq rabbitmqadmin list queues name messages >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] RabbitMQ queues operational
) else (
    echo [WARNING] Could not verify RabbitMQ queues
)

REM Check Redis cache
echo [*] Checking Redis cache...
docker exec redis redis-cli dbsize >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis cache operational
) else (
    echo [WARNING] Could not verify Redis cache
)
echo.

REM ============================================================================
REM STEP 7: Launch Monitoring Dashboard
REM ============================================================================
echo [STEP 7/7] Launching Trading Monitor...
echo.
echo ================================================================================
echo.
echo [*] Starting live trading monitor in 3 seconds...
echo [*] Press Ctrl+C to stop monitoring
echo.
echo     Monitor Features:
echo       - Real-time balance tracking with P/L
echo       - Live trade entry/exit notifications
echo       - Performance statistics by pair
echo       - Recent activity feed (2-hour window)
echo       - Sentiment headline ticker from Redis cache
echo       - Auto-refresh every 15 seconds
echo.
echo     Management URLs:
echo       - RabbitMQ UI:  http://localhost:15672 (admin/cryptoboy_secret)
echo       - Redis CLI:    docker exec -it redis redis-cli
echo.
echo ================================================================================
echo.

timeout /t 3 /nobreak >nul

REM Sync database from container
echo [*] Syncing database...
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1

REM Launch monitor in live mode
python scripts/monitor_trading.py --interval 15

goto CLEANUP

REM ============================================================================
REM LEGACY MODE
REM ============================================================================
:LEGACY_MODE
echo ================================================================================
echo   LEGACY MONOLITHIC MODE
echo ================================================================================
echo.
echo [STEP 1/3] Checking Docker...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    pause
    exit /b 1
)
echo [OK] Docker is running
echo.

echo [STEP 2/3] Starting Trading Bot (Legacy Mode)...
docker ps | findstr "trading-bot-app" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Trading bot is already running
) else (
    docker-compose up -d trading-bot-app >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to start trading bot!
        pause
        exit /b 1
    )
    echo [OK] Trading bot started
)
echo.
echo [*] Waiting for bot initialization...
timeout /t 5 /nobreak >nul
echo.

echo [STEP 3/3] Launching Monitor...
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1
python scripts/monitor_trading.py --interval 15
goto CLEANUP

REM ============================================================================
REM STATUS CHECK ONLY
REM ============================================================================
:STATUS_CHECK
echo ================================================================================
echo   STATUS CHECK MODE
echo ================================================================================
echo.
call check_status.bat
exit /b 0

REM ============================================================================
REM Cleanup on Exit
REM ============================================================================
:CLEANUP
echo.
echo.
echo ================================================================================
echo Monitor stopped. All services are still running in background.
echo ================================================================================
echo.
echo Quick Commands:
echo   - View all logs:      docker-compose logs -f
echo   - Service logs:       docker logs [service-name] -f
echo   - RabbitMQ UI:        http://localhost:15672
echo   - Restart system:     docker-compose restart
echo   - Stop all:           docker-compose down
echo   - Start monitor:      start_monitor.bat
echo.
echo Services: rabbitmq, redis, market-streamer, news-poller,
echo           sentiment-processor, signal-cacher, trading-bot-app
echo.
echo VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
pause
