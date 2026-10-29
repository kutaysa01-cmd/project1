@echo off
REM Build the vector DB from data\tickets and data\manuals
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
    echo [HATA] Once setup.bat calistir
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
python -m src.ingest %*
pause
