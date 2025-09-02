@echo off
echo ========================================
echo    Bitcoin Analyzer Pro - Launcher
echo ========================================
echo.

REM Utiliser Python 3.10 directement
set PYTHON_PATH=C:\Users\nedas\AppData\Local\Programs\Python\Python310\python.exe

echo Verification de Python...
%PYTHON_PATH% --version

echo.
echo Installation des dependances...
%PYTHON_PATH% -m pip install --quiet ccxt ta scipy pytz Pillow streamlit pandas numpy plotly

echo.
echo Lancement de l'application...
%PYTHON_PATH% -m streamlit run app.py

pause