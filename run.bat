@echo off
REM JMA Weather Desktop GUI System - Installation and Run Script
REM 農業部水產試驗所 漁海況研究小組

echo ================================================
echo   JMA 氣象海況展示系統 - 安裝與啟動
echo   農業部水產試驗所 漁海況研究小組
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未偵測到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 正在檢查虛擬環境...
if not exist "venv" (
    echo 正在建立虛擬環境...
    python -m venv venv
)

echo [2/3] 正在啟動虛擬環境並安裝套件...
call venv\Scripts\activate.bat

pip install --upgrade pip
pip install numpy scipy pandas matplotlib cartopy PyQt5 requests tqdm

echo [3/3] 正在啟動應用程式...
python main.py

pause
