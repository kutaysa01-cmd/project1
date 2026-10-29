@echo off
REM =====================================================
REM T3000 Problem Finder - Windows Setup Script
REM =====================================================
setlocal

echo.
echo ============================================
echo  T3000 Problem Finder - Setup
echo ============================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi!
    echo        https://www.python.org/downloads/ adresinden Python 3.10+ kur
    echo        Kurulumda "Add Python to PATH" seceneğini isaretle
    pause
    exit /b 1
)
echo [OK] Python bulundu
python --version

REM --- Create venv ---
if not exist "venv" (
    echo [INFO] Sanal ortam olusturuluyor...
    python -m venv venv
    if errorlevel 1 (
        echo [HATA] venv olusturulamadi
        pause
        exit /b 1
    )
) else (
    echo [OK] Sanal ortam zaten var
)

REM --- Install deps ---
echo [INFO] Pythonpaketleri yukleniyor (ilk kez 5-10 dakika surebilir)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [HATA] Paket kurulumu basarisiz
    pause
    exit /b 1
)

REM --- Check Ollama ---
echo.
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [UYARI] Ollama bulunamadi!
    echo         https://ollama.com adresinden indir ve kur
    echo         Kurulumdan sonra: ollama pull qwen2.5:7b
) else (
    echo [OK] Ollama bulundu
    ollama --version
    echo [INFO] Qwen2.5 7B model kontrol ediliyor...
    ollama list | findstr /i "qwen2.5:7b" >nul
    if errorlevel 1 (
        echo [INFO] Model indiriliyor (~4.5 GB, bir kerelik)...
        ollama pull qwen2.5:7b
    ) else (
        echo [OK] Model zaten yuklu
    )
)

echo.
echo ============================================
echo  Kurulum tamamlandi!
echo ============================================
echo.
echo Sonraki adimlar:
echo   1. data\tickets\ klasorune HTML ticket'larini kopyala
echo   2. data\manuals\ klasorune PDF manuelleri kopyala (opsiyonel)
echo   3. ingest.bat calistir (veritabanini olusturur)
echo   4. run.bat ile uygulamayi ac
echo.
pause
