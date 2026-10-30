@echo off
setlocal
title Ivy - Centro de Comando
cd /d "%~dp0Dashboard"

where node >nul 2>nul
if errorlevel 1 (
  echo O Node.js nao foi encontrado neste computador.
  echo Instale o Node.js e tente novamente.
  pause
  exit /b 1
)

if not exist "node_modules\.bin\next.cmd" (
  echo Preparando o dashboard da Ivy pela primeira vez...
  call npm.cmd ci
  if errorlevel 1 (
    echo Nao foi possivel preparar o dashboard.
    pause
    exit /b 1
  )
)

echo Iniciando o centro de comando da Ivy...
start "Ivy Dashboard Server" /min powershell.exe -NoProfile -WindowStyle Hidden -Command "Set-Location -LiteralPath '%CD%'; & npm.cmd run dev"
timeout /t 7 /nobreak >nul
start "" "http://localhost:3000"

echo O dashboard foi aberto no navegador.
echo Esta janela pode ser fechada.
pause
