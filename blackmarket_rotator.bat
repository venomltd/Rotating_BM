@echo off
title DayZ Blackmarket Rotator v2.0

:menu
echo ===============================================
echo    DayZ Blackmarket Rotator v2.0
echo ===============================================
echo.
echo Please select an option:
echo.
echo 1. Install/Update Dependencies
echo 2. Rotate All Enabled Servers (Manual)
echo 3. Rotate Specific Server
echo 4. List Configured Servers
echo 5. Start Automated Scheduler
echo 6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto rotate_all
if "%choice%"=="3" goto rotate_specific
if "%choice%"=="4" goto list_servers
if "%choice%"=="5" goto scheduler
if "%choice%"=="6" goto exit
echo Invalid choice. Please try again.
echo.
pause
goto menu

:install
echo.
echo Installing/Updating Python dependencies...
pip install requests schedule
echo.
echo Dependencies installed successfully!
pause
goto menu

:rotate_all
echo.
echo Running blackmarket rotation for all enabled servers...
cd /d "%~dp0"
python blackmarket_rotator_main.py
echo.
pause
goto menu

:rotate_specific
echo.
echo Available servers:
python blackmarket_rotator_main.py --list
echo.
set /p server_id="Enter server ID to rotate: "
echo.
echo Rotating server: %server_id%
python blackmarket_rotator_main.py --server %server_id%
echo.
pause
goto menu

:list_servers
echo.
echo Configured servers:
python blackmarket_rotator_main.py --list
echo.
pause
goto menu

:scheduler
echo.
echo Starting Automated Scheduler...
echo Times are configured in config.json
echo Press Ctrl+C to stop the scheduler
echo.
python blackmarket_rotator_main.py --scheduler
pause
goto menu

:exit
echo.
echo Thank you for using DayZ Blackmarket Rotator!
exit /b 0
