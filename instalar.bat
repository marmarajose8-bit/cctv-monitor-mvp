@echo off
REM =============================================================
REM instalar.bat — Instalador unico del Monitor CCTV Inteligente (Windows)
REM =============================================================
REM Uso: doble clic en este archivo, o correr una sola vez desde
REM      PowerShell/CMD con:  instalar.bat
REM
REM Que hace:
REM   1. Crea el entorno virtual e instala dependencias de Python.
REM   2. Te pide interactivamente tus llaves/credenciales y arma el .env
REM      (solo si no existe todavia, para no pisar uno ya configurado).
REM   3. Registra el monitor como Tarea Programada que arranca al iniciar
REM      sesion, corriendo con pythonw.exe (SIN ventana de consola visible).
REM
REM Requisito previo (una sola vez, manual, no automatizable de forma
REM segura desde un script): tener instalado Visual Studio Build Tools
REM (C++) y CMake, necesarios para compilar dlib. Ver README.md.
REM =============================================================

setlocal enabledelayedexpansion
set "PROYECTO_DIR=%~dp0"
cd /d "%PROYECTO_DIR%"

echo =============================================
echo  Instalador del Monitor CCTV Inteligente
echo =============================================
echo Proyecto detectado en: %PROYECTO_DIR%
echo.

REM ---------- 0. Verificar Python ----------
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encontro Python en el PATH.
    echo Instala Python 3.10+ desde https://www.python.org/downloads/
    echo y marca la casilla "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

REM ---------- 1. Entorno virtual ----------
echo [1/4] Creando entorno virtual e instalando librerias de Python...
if not exist "venv\" (
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo ERROR instalando dependencias. Lo mas probable es que falte
    echo Visual Studio Build Tools ^(C++^) o CMake para compilar dlib.
    echo Revisa el README.md, seccion "Instalacion en Windows".
    pause
    exit /b 1
)
call venv\Scripts\deactivate.bat
echo     Listo.

REM ---------- 2. Configuracion (.env) ----------
if exist ".env" (
    echo [2/4] Ya existe un .env, no se sobreescribe.
) else (
    echo [2/4] Vamos a configurar tus credenciales ^(solo se guardan en tu maquina^).
    set /p GK1="  Llave Gemini 1: "
    set /p GK2="  Llave Gemini 2 (Enter para omitir): "
    set /p GK3="  Llave Gemini 3 (Enter para omitir): "
    set /p GK4="  Llave Gemini 4 (Enter para omitir): "
    set /p GK5="  Llave Gemini 5 (Enter para omitir): "
    set /p FDB="  URL de Firebase Realtime Database: "
    set /p FBUCKET="  Storage Bucket de Firebase: "
    set /p CAPINT="  Intervalo de captura en segundos [300]: "
    if "!CAPINT!"=="" set CAPINT=300

    (
        echo GEMINI_KEY_1=!GK1!
        echo GEMINI_KEY_2=!GK2!
        echo GEMINI_KEY_3=!GK3!
        echo GEMINI_KEY_4=!GK4!
        echo GEMINI_KEY_5=!GK5!
        echo(
        echo FIREBASE_CRED_PATH=%PROYECTO_DIR%firebase_credentials.json
        echo FIREBASE_DB_URL=!FDB!
        echo FIREBASE_STORAGE_BUCKET=!FBUCKET!
        echo(
        echo CAPTURE_INTERVAL=!CAPINT!
        echo LOG_FILE_PATH=%PROYECTO_DIR%monitor.log
    ) > ".env"
    echo     .env creado.

    if not exist "firebase_credentials.json" (
        echo.
        echo     ATENCION: falta el archivo firebase_credentials.json
        echo     Descargalo desde Firebase Console -^> Configuracion del proyecto -^>
        echo     Cuentas de servicio -^> Generar nueva clave privada, y colocalo en:
        echo     %PROYECTO_DIR%firebase_credentials.json
    )
)

REM ---------- 3. Tarea programada (arranque automatico sin consola) ----------
echo [3/4] Registrando arranque automatico...

REM pythonw.exe = igual que python.exe pero SIN ventana de consola
set "PYTHONW=%PROYECTO_DIR%venv\Scripts\pythonw.exe"

schtasks /Query /TN "CCTV-Monitor" >nul 2>nul
if not errorlevel 1 (
    schtasks /Delete /TN "CCTV-Monitor" /F >nul
)

schtasks /Create /TN "CCTV-Monitor" /TR "\"%PYTHONW%\" \"%PROYECTO_DIR%main.py\"" /SC ONLOGON /RL LIMITED /F >nul

if errorlevel 1 (
    echo ADVERTENCIA: no se pudo crear la tarea programada automaticamente.
    echo Puedes crearla manualmente con el Programador de Tareas de Windows.
) else (
    echo     Tarea "CCTV-Monitor" registrada: arrancara sola en cada inicio de sesion.
)

REM ---------- 3b. Icono de activacion (barra de tareas) ----------
echo [3b/4] Registrando el icono de activacion/desactivacion...

schtasks /Query /TN "CCTV-Monitor-Tray" >nul 2>nul
if not errorlevel 1 (
    schtasks /Delete /TN "CCTV-Monitor-Tray" /F >nul
)

schtasks /Create /TN "CCTV-Monitor-Tray" /TR "\"%PYTHONW%\" \"%PROYECTO_DIR%tray.py\"" /SC ONLOGON /RL LIMITED /F >nul

if errorlevel 1 (
    echo ADVERTENCIA: no se pudo registrar el icono automaticamente.
) else (
    echo     Icono "CCTV-Monitor-Tray" registrado: aparecera en la barra de tareas
    echo     en cada inicio de sesion. IMPORTANTE: el monitoreo arranca APAGADO
    echo     hasta que actives con el PIN desde ese icono.
)

REM ---------- 4. Arranque inmediato ----------
echo [4/4] Iniciando el monitor y el icono de activacion ahora mismo...
schtasks /Run /TN "CCTV-Monitor" >nul
schtasks /Run /TN "CCTV-Monitor-Tray" >nul

echo.
echo =============================================
echo  Instalacion completa.
echo  El motor de monitoreo ya esta corriendo en
echo  segundo plano (sin ventana visible), pero
echo  arranca APAGADO por seguridad.
echo.
echo  Busca el icono redondo en la barra de tareas
echo  (junto al reloj) para ACTIVARLO con tu PIN
echo  cuando empieces tu turno, y DESACTIVARLO
echo  cuando termines.
echo =============================================
echo.
echo Comandos utiles (opcionales, abrir CMD o PowerShell):
echo   Ver si esta activo:  schtasks /Query /TN "CCTV-Monitor"
echo   Ver logs:            type monitor.log
echo   Detenerlo ahora:     schtasks /End /TN "CCTV-Monitor"
echo   Quitar el arranque:  schtasks /Delete /TN "CCTV-Monitor" /F
echo.
pause
