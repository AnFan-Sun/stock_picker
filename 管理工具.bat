@echo off
title Stock Picker Manager

:MENU
cls
echo ========================================
echo        Stock Picker - Manager
echo ========================================
echo.
echo   1. Start (background silent mode)
echo   2. Check status
echo   3. Stop
echo   4. Exit
echo.
echo ========================================
set /p choice=Enter option (1-4): 

if "%choice%"=="1" goto START
if "%choice%"=="2" goto STATUS
if "%choice%"=="3" goto STOP
if "%choice%"=="4" goto EXIT

echo.
echo Invalid option, please try again!
pause
goto MENU

:START
cls
echo ========================================
echo   Start Stock Picker
echo ========================================
echo.

tasklist /FI "IMAGENAME eq stock_picker.exe" 2>nul | find /I "stock_picker.exe" >nul
if %ERRORLEVEL%==0 (
    echo ========================================
    echo   [ALREADY RUNNING]
    echo ========================================
    echo.
    echo   Stock Picker is already running!
    echo.
    echo   No need to start again.
    echo.
    echo ========================================
    echo.
    pause
    goto MENU
)

echo Starting Stock Picker...
start "" wscript.exe "D:\tools\stock\stock_picker\start_silent.vbs"

timeout /t 3 /nobreak >nul

tasklist /FI "IMAGENAME eq stock_picker.exe" 2>nul | find /I "stock_picker.exe" >nul
if %ERRORLEVEL%==0 (
    echo.
    echo ========================================
    echo   [STARTED SUCCESSFULLY]
    echo ========================================
    echo.
    echo   Stock Picker started successfully!
    echo.
    echo   It will run in background silently.
    echo.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   [START FAILED]
    echo ========================================
    echo.
    echo   Failed to start Stock Picker.
    echo   Please check your configuration.
    echo.
    echo ========================================
)

echo.
pause
goto MENU

:STATUS
cls
echo ========================================
echo   Status
echo ========================================
echo.

tasklist /FI "IMAGENAME eq stock_picker.exe" 2>nul | find /I "stock_picker.exe" >nul
if %ERRORLEVEL%==0 (
    echo   [RUNNING]
    echo.
    echo   Stock Picker is running.
    echo.
    tasklist /FI "IMAGENAME eq stock_picker.exe"
) else (
    echo   [NOT RUNNING]
    echo.
    echo   Stock Picker is not running.
)

echo.
echo ========================================
echo.
pause
goto MENU

:STOP
cls
echo ========================================
echo   Stop Stock Picker
echo ========================================
echo.

tasklist /FI "IMAGENAME eq stock_picker.exe" 2>nul | find /I "stock_picker.exe" >nul
if %ERRORLEVEL%==1 (
    echo   [NOT RUNNING]
    echo.
    echo   No running process found.
    echo.
    echo ========================================
    echo.
    pause
    goto MENU
)

echo Stopping Stock Picker...
taskkill /F /IM stock_picker.exe >nul 2>&1

timeout /t 1 /nobreak >nul

tasklist /FI "IMAGENAME eq stock_picker.exe" 2>nul | find /I "stock_picker.exe" >nul
if %ERRORLEVEL%==1 (
    echo.
    echo ========================================
    echo   [STOPPED SUCCESSFULLY]
    echo ========================================
    echo.
    echo   All processes stopped.
    echo.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   [STILL RUNNING]
    echo ========================================
    echo.
    echo   Failed to stop all processes.
    echo.
    echo   Please try stopping from Task Manager.
    echo.
    echo ========================================
)

echo.
pause
goto MENU

:EXIT
cls
exit
