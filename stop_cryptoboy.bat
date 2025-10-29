@echo off
REM CryptoBoy Microservice Shutdown Script
REM VoidCat RDC - Graceful Service Shutdown

TITLE CryptoBoy System Shutdown - VoidCat RDC
COLOR 0C

echo.
echo ================================================================================
echo   CRYPTOBOY SYSTEM SHUTDOWN - VOIDCAT RDC
echo ================================================================================
echo.

REM Enable ANSI colors
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

echo Select shutdown mode:
echo   [1] Stop All Services (preserve containers)
echo   [2] Stop and Remove All (complete cleanup)
echo   [3] Stop Trading Bot Only
echo   [4] Cancel
echo.
set /p mode="Enter choice (1-4): "
echo.

if "%mode%"=="4" goto CANCEL
if "%mode%"=="3" goto STOP_BOT_ONLY
if "%mode%"=="2" goto FULL_CLEANUP
if not "%mode%"=="1" (
    echo [ERROR] Invalid choice. Exiting...
    timeout /t 2 /nobreak >nul
    exit /b 1
)

REM ============================================================================
REM STOP ALL SERVICES
REM ============================================================================
:STOP_ALL
echo [*] Stopping all services...
echo.

echo [1/2] Stopping Trading Bot...
docker-compose stop trading-bot-app >nul 2>&1
echo [OK] Trading bot stopped

echo [2/2] Stopping Microservices...
docker-compose stop market-streamer news-poller sentiment-processor signal-cacher >nul 2>&1
echo [OK] Microservices stopped

echo [3/3] Stopping Infrastructure...
docker-compose stop rabbitmq redis >nul 2>&1
echo [OK] Infrastructure stopped

echo.
echo [SUCCESS] All services stopped. Containers preserved for restart.
echo.
goto END

REM ============================================================================
REM FULL CLEANUP
REM ============================================================================
:FULL_CLEANUP
echo [WARNING] This will remove all containers, networks, and volumes.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

echo [*] Performing full cleanup...
docker-compose down -v >nul 2>&1
echo [OK] All containers, networks, and volumes removed

echo.
echo [SUCCESS] Complete cleanup finished.
echo.
goto END

REM ============================================================================
REM STOP BOT ONLY
REM ============================================================================
:STOP_BOT_ONLY
echo [*] Stopping trading bot only...
docker-compose stop trading-bot-app >nul 2>&1
echo [OK] Trading bot stopped. Microservices continue running.
echo.
goto END

REM ============================================================================
REM CANCEL
REM ============================================================================
:CANCEL
echo [*] Shutdown cancelled.
echo.
goto END

REM ============================================================================
REM END
REM ============================================================================
:END
echo ================================================================================
echo VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
pause
