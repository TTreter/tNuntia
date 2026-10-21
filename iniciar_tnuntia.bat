@echo off
chcp 65001 >nul
title tNuntia - Servidor Local (Porta 8001)
cd /d "%~dp0"

echo ============================================================
echo   Iniciando tNuntia no Windows...
echo ============================================================

set PYTHONIOENCODING=utf-8

REM Verifica se existe ambiente virtual local (.venv ou venv), senao usa o Python global
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_server.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" run_server.py
) else (
    python run_server.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O servidor encerrou com erro. Verifique se o Python esta instalado.
    pause
)
