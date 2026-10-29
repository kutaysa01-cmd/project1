@echo off
REM Launch the T3000 Problem Finder GUI
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Once setup.bat calistir
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM Start Ollama in the background if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if errorlevel 1 (
    echo [INFO] Ollama baslatiliyor...
    start "" /B ollama serve
    timeout /t 3 /nobreak >nul
)

python -m src.app
