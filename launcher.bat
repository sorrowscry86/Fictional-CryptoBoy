@echo off
REM CryptoBoy Main Launcher Menu
REM VoidCat RDC - Unified System Control

TITLE CryptoBoy Launcher - VoidCat RDC
COLOR 0B

:MENU
cls
echo.
echo ================================================================================
echo                   CRYPTOBOY TRADING SYSTEM - VOIDCAT RDC
echo                      Microservice Architecture Control Panel
echo ================================================================================
echo.
echo   [SYSTEM OPERATIONS]
echo     1. Start CryptoBoy (Microservice Mode)
echo     2. Start CryptoBoy (Legacy Monolithic Mode)
echo     3. Stop All Services
echo     4. Restart Service
echo     5. Check System Status
echo.
echo   [MONITORING]
echo     6. Launch Trading Monitor
echo     7. View Service Logs
echo     8. Open RabbitMQ UI (Browser)
echo.
echo   [UTILITIES]
echo     9. Run Data Pipeline
echo    10. Run Backtest
echo    11. Add to Windows Startup
echo    12. Remove from Windows Startup
echo.
echo    0. Exit
echo.
echo ================================================================================
echo.
set /p choice="Enter your choice (0-12): "

if "%choice%"=="0" goto EXIT
if "%choice%"=="1" goto START_MICRO
if "%choice%"=="2" goto START_LEGACY
if "%choice%"=="3" goto STOP
if "%choice%"=="4" goto RESTART
if "%choice%"=="5" goto STATUS
if "%choice%"=="6" goto MONITOR
if "%choice%"=="7" goto LOGS
if "%choice%"=="8" goto RABBITMQ_UI
if "%choice%"=="9" goto DATA_PIPELINE
if "%choice%"=="10" goto BACKTEST
if "%choice%"=="11" goto ADD_STARTUP
if "%choice%"=="12" goto REMOVE_STARTUP

echo.
echo [ERROR] Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto MENU

:START_MICRO
cls
start_cryptoboy.bat
goto MENU

:START_LEGACY
cls
set mode=2
start_cryptoboy.bat
goto MENU

:STOP
cls
call stop_cryptoboy.bat
goto MENU

:RESTART
cls
call restart_service.bat
goto MENU

:STATUS
cls
call check_status.bat
goto MENU

:MONITOR
cls
call start_monitor.bat
goto MENU

:LOGS
cls
call view_logs.bat
goto MENU

:RABBITMQ_UI
echo.
echo [*] Opening RabbitMQ Management UI in your default browser...
echo     URL: http://localhost:15672
echo     Default credentials: admin / cryptoboy_secret
echo.
start http://localhost:15672
timeout /t 2 /nobreak >nul
goto MENU

:DATA_PIPELINE
cls
echo.
echo [*] Running data pipeline...
python scripts/run_data_pipeline.py
echo.
pause
goto MENU

:BACKTEST
cls
echo.
echo [*] Running backtest...
python backtest/run_backtest.py
echo.
pause
goto MENU

:ADD_STARTUP
cls
call add_to_startup.bat
goto MENU

:REMOVE_STARTUP
cls
call remove_from_startup.bat
goto MENU

:EXIT
cls
echo.
echo ================================================================================
echo   Thank you for using CryptoBoy Trading System
echo   VoidCat RDC - Excellence in Automated Trading
echo ================================================================================
echo.
exit /b 0
