@echo off
TITLE Remove CryptoBoy from Windows Startup

echo.
echo ================================================================
echo   Remove CryptoBoy from Windows Startup - VoidCat RDC
echo ================================================================
echo.

REM Get Startup folder path
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\CryptoBoy Trading System.lnk

echo Checking for startup shortcut...
echo.

if exist "%SHORTCUT_PATH%" (
    echo [FOUND] Shortcut exists at:
    echo %SHORTCUT_PATH%
    echo.
    echo Press any key to remove from startup or Ctrl+C to cancel...
    pause >nul
    
    del "%SHORTCUT_PATH%"
    
    if not exist "%SHORTCUT_PATH%" (
        echo.
        echo [OK] Successfully removed from Windows startup!
        echo.
        echo CryptoBoy will no longer launch automatically when Windows starts.
    ) else (
        echo.
        echo [ERROR] Failed to remove shortcut. Please delete manually:
        echo %SHORTCUT_PATH%
    )
) else (
    echo [INFO] No startup shortcut found.
    echo CryptoBoy is not currently set to auto-start.
)

echo.
echo ================================================================
echo.
pause
