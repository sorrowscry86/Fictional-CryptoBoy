@echo off
REM CryptoBoy Individual Service Restart
REM VoidCat RDC - Service Management

TITLE CryptoBoy Service Restart - VoidCat RDC

echo.
echo ================================================================================
echo   CRYPTOBOY SERVICE RESTART - VOIDCAT RDC
echo ================================================================================
echo.

echo Select service to restart:
echo   [1] Trading Bot (Freqtrade)
echo   [2] Market Data Streamer
echo   [3] News Poller
echo   [4] Sentiment Processor
echo   [5] Signal Cacher
echo   [6] RabbitMQ
echo   [7] Redis
echo   [8] All Microservices (not infrastructure)
echo   [9] Entire System
echo.
set /p choice="Enter choice (1-9): "
echo.

if "%choice%"=="1" goto TRADING_BOT
if "%choice%"=="2" goto MARKET_STREAMER
if "%choice%"=="3" goto NEWS_POLLER
if "%choice%"=="4" goto SENTIMENT_PROCESSOR
if "%choice%"=="5" goto SIGNAL_CACHER
if "%choice%"=="6" goto RABBITMQ
if "%choice%"=="7" goto REDIS
if "%choice%"=="8" goto ALL_MICROSERVICES
if "%choice%"=="9" goto ENTIRE_SYSTEM

echo [ERROR] Invalid choice
timeout /t 2 /nobreak >nul
exit /b 1

:TRADING_BOT
echo [*] Restarting Trading Bot...
docker-compose restart trading-bot-app
echo [OK] Trading Bot restarted
goto END

:MARKET_STREAMER
echo [*] Restarting Market Data Streamer...
docker-compose restart market-streamer
echo [OK] Market Data Streamer restarted
goto END

:NEWS_POLLER
echo [*] Restarting News Poller...
docker-compose restart news-poller
echo [OK] News Poller restarted
goto END

:SENTIMENT_PROCESSOR
echo [*] Restarting Sentiment Processor...
docker-compose restart sentiment-processor
echo [OK] Sentiment Processor restarted
goto END

:SIGNAL_CACHER
echo [*] Restarting Signal Cacher...
docker-compose restart signal-cacher
echo [OK] Signal Cacher restarted
goto END

:RABBITMQ
echo [*] Restarting RabbitMQ...
echo [WARNING] This may cause message loss if queues are not persistent
timeout /t 3 /nobreak >nul
docker-compose restart rabbitmq
echo [OK] RabbitMQ restarted
goto END

:REDIS
echo [*] Restarting Redis...
echo [WARNING] This will clear cached signals
timeout /t 3 /nobreak >nul
docker-compose restart redis
echo [OK] Redis restarted
goto END

:ALL_MICROSERVICES
echo [*] Restarting all microservices...
docker-compose restart market-streamer news-poller sentiment-processor signal-cacher
echo [OK] All microservices restarted
goto END

:ENTIRE_SYSTEM
echo [*] Restarting entire system...
docker-compose restart
echo [OK] Entire system restarted
goto END

:END
echo.
echo ================================================================================
echo VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
pause
