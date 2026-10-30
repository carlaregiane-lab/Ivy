@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Ivy - Assistente de Trabalho
cd /d "%~dp0Projeto"

set "IVY_PYTHON="
where py >nul 2>&1
if not errorlevel 1 set "IVY_PYTHON=py -3"

if not defined IVY_PYTHON (
    where python >nul 2>&1
    if not errorlevel 1 set "IVY_PYTHON=python"
)

if not defined IVY_PYTHON (
    echo.
    echo A Ivy nao encontrou o Python neste computador.
    echo Instale o Python 3.11 ou mais recente e tente novamente.
    echo.
    pause
    exit /b 1
)

set "IVY_VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%IVY_VENV_PYTHON%" (
    echo.
    echo Primeira preparacao da Ivy. Isso pode levar alguns minutos...
    %IVY_PYTHON% -m venv .venv
    if errorlevel 1 (
        echo.
        echo Nao foi possivel criar o ambiente isolado da Ivy.
        pause
        exit /b 1
    )
)

"%IVY_VENV_PYTHON%" -c "import pydantic" >nul 2>&1
if errorlevel 1 (
    echo Instalando os componentes necessarios da Ivy...
    "%IVY_VENV_PYTHON%" -m pip install --disable-pip-version-check -e .
    if errorlevel 1 (
        echo.
        echo A instalacao nao foi concluida. Verifique a internet e tente novamente.
        pause
        exit /b 1
    )
)

echo.
echo =============================================
echo         IVY - ASSISTENTE DE TRABALHO
echo =============================================
echo.

if "%~1"=="" (
    "%IVY_VENV_PYTHON%" ivy.py --assistant --mode auto
    set "IVY_RESULT=!ERRORLEVEL!"
    echo.
    pause
    exit /b !IVY_RESULT!
) else (
    "%IVY_VENV_PYTHON%" ivy.py --mode auto %*
)

set "IVY_RESULT=%ERRORLEVEL%"
exit /b %IVY_RESULT%
