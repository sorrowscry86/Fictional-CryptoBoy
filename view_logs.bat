@echo off
REM CryptoBoy Microservice Log Viewer
REM VoidCat RDC - Real-Time Log Monitoring

TITLE CryptoBoy Log Viewer - VoidCat RDC

echo.
echo ================================================================================
echo   CRYPTOBOY LOG VIEWER - VOIDCAT RDC
echo ================================================================================
echo.

echo Select service to monitor:
echo   [1] All Services (combined)
echo   [2] Trading Bot (Freqtrade)
echo   [3] Market Data Streamer
echo   [4] News Poller
echo   [5] Sentiment Processor
echo   [6] Signal Cacher
echo   [7] RabbitMQ
echo   [8] Redis
echo   [9] Recent Errors Only
echo.
set /p choice="Enter choice (1-9): "
echo.

if "%choice%"=="1" goto ALL_LOGS
if "%choice%"=="2" goto TRADING_BOT
if "%choice%"=="3" goto MARKET_STREAMER
if "%choice%"=="4" goto NEWS_POLLER
if "%choice%"=="5" goto SENTIMENT_PROCESSOR
if "%choice%"=="6" goto SIGNAL_CACHER
if "%choice%"=="7" goto RABBITMQ
if "%choice%"=="8" goto REDIS
if "%choice%"=="9" goto ERRORS_ONLY

echo [ERROR] Invalid choice
timeout /t 2 /nobreak >nul
exit /b 1

:ALL_LOGS
echo [*] Showing all service logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker-compose logs -f --tail 50
goto END

:TRADING_BOT
echo [*] Showing Trading Bot logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 trading-bot-app
goto END

:MARKET_STREAMER
echo [*] Showing Market Data Streamer logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 market-streamer
goto END

:NEWS_POLLER
echo [*] Showing News Poller logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 news-poller
goto END

:SENTIMENT_PROCESSOR
echo [*] Showing Sentiment Processor logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 sentiment-processor
goto END

:SIGNAL_CACHER
echo [*] Showing Signal Cacher logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 signal-cacher
goto END

:RABBITMQ
echo [*] Showing RabbitMQ logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 rabbitmq
goto END

:REDIS
echo [*] Showing Redis logs (live)...
echo [*] Press Ctrl+C to exit
echo.
docker logs -f --tail 100 redis
goto END

:ERRORS_ONLY
echo [*] Showing recent errors from all services...
echo.
docker-compose logs --tail 200 | findstr /I "error exception failed warning critical"
echo.
echo [*] End of error log
goto END

:END
echo.
pause
