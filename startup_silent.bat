@echo off
REM ============================================================================
REM CryptoBoy Silent Startup Launcher
REM Optimized for Windows Startup - Minimal user interaction
REM VoidCat RDC
REM ============================================================================

REM Navigate to project directory
cd /d "%~dp0"

REM Check if Docker is running (silent check)
docker version >nul 2>&1
if %errorlevel% neq 0 (
    REM Docker not running - create notification
    echo Docker Desktop is not running. > "%TEMP%\cryptoboy_startup_error.txt"
    echo CryptoBoy trading bot requires Docker Desktop. >> "%TEMP%\cryptoboy_startup_error.txt"
    echo. >> "%TEMP%\cryptoboy_startup_error.txt"
    echo Please: >> "%TEMP%\cryptoboy_startup_error.txt"
    echo 1. Start Docker Desktop >> "%TEMP%\cryptoboy_startup_error.txt"
    echo 2. Run start_cryptoboy.bat manually >> "%TEMP%\cryptoboy_startup_error.txt"
    
    REM Show error notification (Windows 10/11)
    powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Docker Desktop is not running. Please start Docker Desktop first.', 'CryptoBoy Startup', 'OK', 'Warning')" >nul 2>&1
    exit /b 1
)

REM Wait a bit for Docker to be fully ready
timeout /t 3 /nobreak >nul

REM Check if container exists and start it
docker ps -a | findstr "trading-bot-app" >nul 2>&1
if %errorlevel% equ 0 (
    REM Container exists, make sure it's running
    docker ps | findstr "trading-bot-app" >nul 2>&1
    if %errorlevel% neq 0 (
        REM Container exists but not running, start it
        docker start trading-bot-app >nul 2>&1
    )
) else (
    REM Container doesn't exist, create it
    docker-compose up -d >nul 2>&1
)

REM Wait for bot to initialize
timeout /t 8 /nobreak >nul

REM Optional: Launch monitor in minimized window
REM Uncomment the next line if you want the monitor to auto-start
REM start /MIN cmd /c "docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >nul 2>&1 && python scripts/monitor_trading.py --interval 15"

REM Success notification (silent - just log)
echo [%date% %time%] CryptoBoy trading bot started successfully >> logs\startup.log 2>&1

exit /b 0
