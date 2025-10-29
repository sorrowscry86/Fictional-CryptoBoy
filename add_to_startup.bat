@echo off
TITLE Add CryptoBoy to Windows Startup

echo.
echo ================================================================
echo     Add CryptoBoy to Windows Startup - VoidCat RDC
echo ================================================================
echo.

REM Get Startup folder path
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo Startup folder: %STARTUP_FOLDER%
echo.

echo This will create a shortcut in your Windows Startup folder.
echo CryptoBoy will automatically launch when Windows starts.
echo.
echo Choose startup mode:
echo   [1] SILENT MODE - Bot runs in background (recommended)
echo   [2] FULL MODE - Bot + Monitor window opens
echo.
set /p CHOICE="Enter choice (1 or 2): "

if "%CHOICE%"=="1" (
    set TARGET_SCRIPT=startup_silent.bat
    set MODE_DESC=Silent Mode - Bot only
    set WINDOW_STYLE=7
) else if "%CHOICE%"=="2" (
    set TARGET_SCRIPT=start_cryptoboy.bat
    set MODE_DESC=Full Mode - Bot + Monitor
    set WINDOW_STYLE=1
) else (
    echo.
    echo [ERROR] Invalid choice. Please run again and select 1 or 2.
    pause
    exit /b 1
)

echo.
echo Selected: %MODE_DESC%
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

REM Create VBScript to make shortcut
set SCRIPT="%TEMP%\create_startup_shortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = "%STARTUP_FOLDER%\CryptoBoy Trading System.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0%TARGET_SCRIPT%" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "CryptoBoy Trading System - Auto-start (%MODE_DESC%)" >> %SCRIPT%
echo oLink.IconLocation = "C:\Windows\System32\shell32.dll,41" >> %SCRIPT%
echo oLink.WindowStyle = %WINDOW_STYLE% >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

REM Execute VBScript
cscript //nologo %SCRIPT%
del %SCRIPT%

echo.
echo [OK] Startup shortcut created successfully!
echo.
echo Mode: %MODE_DESC%
echo Location: %STARTUP_FOLDER%
echo Shortcut: CryptoBoy Trading System.lnk
echo.
echo ================================================================
echo IMPORTANT: What happens on startup
echo ================================================================
echo.
echo When Windows starts, CryptoBoy will:
echo   1. Check if Docker Desktop is running
echo   2. Start the trading bot container
if "%CHOICE%"=="2" (
    echo   3. Launch the monitoring dashboard
) else (
    echo   3. Run silently in background
)
echo.
echo NOTES:
echo   - Docker Desktop must be set to start with Windows
if "%CHOICE%"=="2" (
    echo   - The monitor window will open automatically
    echo   - You can close the monitor anytime (bot keeps running)
) else (
    echo   - Bot runs silently (no window opens)
    echo   - Use start_monitor.bat to view status anytime
)
echo   - Logs saved to: logs\startup.log
echo.
echo To configure Docker Desktop auto-start:
echo   1. Open Docker Desktop
echo   2. Settings ^> General
echo   3. Check "Start Docker Desktop when you log in"
echo.
echo To REMOVE from startup:
echo   1. Press Win+R
echo   2. Type: shell:startup
echo   3. Delete "CryptoBoy Trading System.lnk"
echo.
echo ================================================================
echo.
pause
