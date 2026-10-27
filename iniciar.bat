@echo off
setlocal EnableExtensions
title LogiFlow API
cd /d "%~dp0"

rem ==================================================================
rem  LogiFlow API - inicializacao em computadores Windows
rem
rem  Na primeira execucao: cria o ambiente Python (.venv), instala as
rem  dependencias, gera o .env, cria o banco e pede os dados do
rem  Administrador. Nas proximas, apenas inicia a API.
rem
rem  Configuracao (edite abaixo ou defina antes de executar):
rem    LOGIFLOW_HOST=127.0.0.1  somente este computador acessa
rem    LOGIFLOW_HOST=0.0.0.0    outros computadores da rede acessam
rem                             (o Windows pode pedir liberacao no firewall)
rem    LOGIFLOW_PORTA=8000
rem    LOGIFLOW_PROCESSOS=2     processos do servidor (padrao: metade dos
rem                             nucleos, entre 1 e 4); mais processos = mais
rem                             requisicoes por segundo e mais memoria
rem
rem  Sem internet: copie para a pasta "pacotes" os arquivos gerados por
rem    pip download -r requirements.txt -d pacotes
rem  em um computador com a mesma versao do Python.
rem ==================================================================

if not defined LOGIFLOW_HOST set "LOGIFLOW_HOST=127.0.0.1"
if not defined LOGIFLOW_PORTA set "LOGIFLOW_PORTA=8000"
if not defined LOGIFLOW_PROCESSOS set /a "LOGIFLOW_PROCESSOS=NUMBER_OF_PROCESSORS / 2"
if %LOGIFLOW_PROCESSOS% LSS 1 set "LOGIFLOW_PROCESSOS=1"
if %LOGIFLOW_PROCESSOS% GTR 4 set "LOGIFLOW_PROCESSOS=4"

echo.
echo ===== LogiFlow API =====
echo.

rem --- 1. Python 3.11 ou superior ---
set "PYTHON_BASE="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PYTHON_BASE=py -3"
if not defined PYTHON_BASE (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PYTHON_BASE=python"
)
if not defined PYTHON_BASE (
    echo [ERRO] Python 3.11 ou superior nao foi encontrado.
    echo        Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH"
    echo        e execute este arquivo novamente.
    goto :falha
)

rem --- Porta livre? No Windows dois servidores conseguem abrir a mesma porta e
rem     dividir as conexoes; por isso a verificacao vem antes de tocar no banco.
netstat -ano -p tcp | findstr /r /c:":%LOGIFLOW_PORTA% .*LISTENING" >nul
if not errorlevel 1 (
    echo [ERRO] A porta %LOGIFLOW_PORTA% ja esta em uso. O LogiFlow ja esta aberto em outra janela?
    echo        Feche a outra janela ou mude LOGIFLOW_PORTA neste arquivo.
    echo        Se nao houver outra janela, reinicie o computador ou encerre os processos
    echo        python.exe no Gerenciador de Tarefas.
    goto :falha
)

rem --- 2. Ambiente virtual ---
if not exist ".venv\Scripts\python.exe" (
    echo Criando o ambiente virtual .venv ...
    %PYTHON_BASE% -m venv .venv
    if errorlevel 1 goto :falha
)
set "PY=%~dp0.venv\Scripts\python.exe"

rem --- 3. Dependencias: instala na primeira vez e quando o requirements.txt mudar ---
set "ORIGEM_PACOTES="
if exist "pacotes\" set "ORIGEM_PACOTES=--no-index --find-links pacotes"
fc /b "requirements.txt" ".venv\requirements.instalado" >nul 2>nul
if errorlevel 1 (
    echo Instalando as dependencias. Na primeira vez pode levar alguns minutos...
    "%PY%" -m pip install --disable-pip-version-check -q %ORIGEM_PACOTES% -r requirements.txt
    if errorlevel 1 goto :falha
    copy /y "requirements.txt" ".venv\requirements.instalado" >nul
)

rem --- 4. .env, banco de dados, Administrador e dados de demonstracao ---
"%PY%" -m scripts.preparar
if errorlevel 1 goto :falha

rem --- 5. Inicia a API ---
echo.
echo API disponivel em: http://127.0.0.1:%LOGIFLOW_PORTA%/interface
if "%LOGIFLOW_HOST%"=="0.0.0.0" (
    echo Nos outros computadores da rede, troque 127.0.0.1 pelo IPv4 deste computador:
    ipconfig | findstr /c:"IPv4"
)
echo Processos do servidor: %LOGIFLOW_PROCESSOS%
echo Para encerrar, feche esta janela ou pressione Ctrl+C.
echo.
if not defined LOGIFLOW_SEM_NAVEGADOR (
    start "" /b cmd /c "ping -n 6 127.0.0.1 >nul & start http://127.0.0.1:%LOGIFLOW_PORTA%/interface"
)
"%PY%" -m uvicorn app.main:app --host %LOGIFLOW_HOST% --port %LOGIFLOW_PORTA% --workers %LOGIFLOW_PROCESSOS%
if errorlevel 1 goto :falha
exit /b 0

:falha
echo.
echo [ERRO] O LogiFlow nao pode ser iniciado. Veja a mensagem acima.
if not defined LOGIFLOW_SEM_PAUSA pause
exit /b 1
