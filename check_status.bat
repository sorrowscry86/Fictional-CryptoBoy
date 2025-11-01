@echo off
REM CryptoBoy Microservice Status Check
REM VoidCat RDC - Comprehensive System Status

TITLE CryptoBoy Status Check - VoidCat RDC

echo.
echo ================================================================================
echo   CRYPTOBOY MICROSERVICE STATUS CHECK - VOIDCAT RDC
echo ================================================================================
echo.

REM Enable ANSI colors
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM Check Docker
echo [INFRASTRUCTURE]
echo.
docker version >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Docker: RUNNING
) else (
    echo [X] Docker: NOT RUNNING
    echo.
    pause
    exit /b 1
)

REM Check all services
echo.
echo [SERVICES STATUS]
echo.
docker ps --format "{{.Names}}: {{.Status}}" | findstr /C:"rabbitmq" /C:"redis" /C:"market-streamer" /C:"news-poller" /C:"sentiment-processor" /C:"signal-cacher" /C:"trading-bot"
echo.

REM Check RabbitMQ queues
echo [RABBITMQ QUEUES]
echo.
docker exec trading-rabbitmq-prod rabbitmqctl list_queues name messages 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Could not connect to RabbitMQ
)
echo.

REM Check Redis keys
echo [REDIS CACHE]
echo.
docker exec trading-redis-prod redis-cli DBSIZE 2>nul
if %errorlevel% equ 0 (
    docker exec trading-redis-prod redis-cli KEYS "sentiment:*" 2>nul
    echo [+] Redis operational
) else (
    echo [WARNING] Could not connect to Redis
)
echo.

REM Check recent container logs for errors
echo [RECENT ERRORS]
echo.
docker-compose logs --tail 20 2>nul | findstr /I "error exception failed"
if %errorlevel% neq 0 (
    echo [+] No recent errors detected
)
echo.

REM Sync database and show trading performance
echo [TRADING PERFORMANCE]
echo.
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1
if %errorlevel% equ 0 (
    python scripts/monitor_trading.py --once
) else (
    echo [WARNING] Could not sync database from trading bot
)

echo.
echo ================================================================================
echo   For detailed monitoring, run: start_monitor.bat
echo   For RabbitMQ UI: http://localhost:15672
echo   VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
pause
