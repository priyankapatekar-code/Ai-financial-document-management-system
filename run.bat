@echo off
setlocal
cd /d "%~dp0"
title AI Financial Document Management System

rem --- Locate or create the virtual environment (prefers ..\venv, then .\venv) ---
set "VENV="
if exist "..\venv\Scripts\activate.bat" set "VENV=..\venv"
if not defined VENV if exist "venv\Scripts\activate.bat" set "VENV=venv"
if not defined VENV (
    echo Creating virtual environment...
    python -m venv venv || goto :fail
    set "VENV=venv"
)

call "%VENV%\Scripts\activate.bat" || goto :fail

rem --- Install requirements only if not done yet or requirements.txt changed ---
set "STAMP=%VENV%\.requirements.installed"
set "NEEDS_INSTALL=1"
if exist "%STAMP%" (
    fc /b requirements.txt "%STAMP%" >nul 2>&1 && set "NEEDS_INSTALL=0"
)
if "%NEEDS_INSTALL%"=="1" (
    echo Installing requirements...
    python -m pip install -r requirements.txt || goto :fail
    copy /y requirements.txt "%STAMP%" >nul
) else (
    echo Requirements already installed.
)

rem --- Run the app and open the browser ---
echo Starting server at http://127.0.0.1:8000/ui/
start "" /min cmd /c "ping -n 5 127.0.0.1 >nul & start "" http://127.0.0.1:8000/ui/"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :fail
goto :eof

:fail
echo.
echo Something went wrong. See the messages above.
pause
exit /b 1
