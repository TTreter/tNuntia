@echo off
chcp 65001 >nul
title Iniciar Ecossistema Legislativo (tVerbum + tNuntia)
cd /d "%~dp0"

echo ============================================================
echo   Iniciando Ecossistema: tVerbum + tNuntia
echo ============================================================
echo.
echo 1. Iniciando tVerbum na porta 8000...
start "tVerbum (Porta 8000)" cmd /k "cd /d "%~dp0..\tVerbum" && call iniciar_tverbum.bat"

echo 2. Iniciando tNuntia na porta 8001...
start "tNuntia (Porta 8001)" cmd /k "cd /d "%~dp0" && call iniciar_tnuntia.bat"

echo.
echo Servidores disparados!
echo - tVerbum: http://localhost:8000
echo - tNuntia: http://localhost:8001
echo.
timeout /t 3 /nobreak >nul
