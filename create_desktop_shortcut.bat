@echo off
TITLE Create CryptoBoy Desktop Shortcut

echo.
echo ================================================================
echo       Creating CryptoBoy Desktop Shortcut - VoidCat RDC
echo ================================================================
echo.

REM Get desktop path
for /f "usebackq tokens=3*" %%A in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop`) do set DESKTOP=%%B
set DESKTOP=%DESKTOP:~0,-1%

REM Expand environment variables
call set DESKTOP=%DESKTOP%

echo Desktop location: %DESKTOP%
echo.

REM Create VBScript to make shortcut
set SCRIPT="%TEMP%\create_shortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = "%DESKTOP%\CryptoBoy Trading System.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0start_cryptoboy.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "CryptoBoy Trading System - VoidCat RDC" >> %SCRIPT%
echo oLink.IconLocation = "C:\Windows\System32\shell32.dll,41" >> %SCRIPT%
echo oLink.WindowStyle = 1 >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

REM Execute VBScript
cscript //nologo %SCRIPT%
del %SCRIPT%

echo.
echo [OK] Desktop shortcut created successfully!
echo.
echo Shortcut name: "CryptoBoy Trading System.lnk"
echo Location: %DESKTOP%
echo.
echo You can now double-click the shortcut from your desktop to:
echo   1. Start Docker (if needed)
echo   2. Launch the trading bot
echo   3. Display the monitoring dashboard
echo.
echo ================================================================
echo.
pause
