@echo off
setlocal
title Genshin Tracker
pushd "%~dp0"
if errorlevel 1 goto folder_error

if not exist "app_v2.py" goto missing_app
if not exist "genshin_v2.db" goto missing_database
if exist ".venv\Scripts\python.exe" goto dependencies

echo Creating the Python environment...
py -3 -m venv .venv
if not errorlevel 1 goto dependencies
python -m venv .venv
if errorlevel 1 goto python_error

:dependencies
".venv\Scripts\python.exe" -c "import fastapi, uvicorn" >nul 2>&1
if not errorlevel 1 goto launch
echo Installing app dependencies. Internet access is needed for this step...
".venv\Scripts\python.exe" -m pip install fastapi uvicorn
if errorlevel 1 goto dependency_error

:launch
".venv\Scripts\python.exe" windows_launcher.py
if errorlevel 1 goto launch_error
popd
exit /b 0

:missing_app
echo Put this launcher and windows_launcher.py in the folder containing app_v2.py.
goto failed
:missing_database
echo genshin_v2.db was not found in this folder.
goto failed
:python_error
echo Python could not create the app environment. Install Python, then try again.
goto failed
:dependency_error
echo Dependencies could not be installed. Check your internet connection and try again.
goto failed
:launch_error
echo The app stopped with an error. See the details above.
goto failed
:folder_error
echo The app folder could not be opened.
pause
exit /b 1
:failed
pause
popd
exit /b 1
