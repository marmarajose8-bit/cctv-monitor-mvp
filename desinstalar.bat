@echo off
REM desinstalar.bat — Quita la tarea programada del Monitor CCTV Inteligente

echo Deteniendo el monitor...
schtasks /End /TN "CCTV-Monitor" >nul 2>nul

echo Quitando el arranque automatico...
schtasks /Delete /TN "CCTV-Monitor" /F >nul 2>nul

if errorlevel 1 (
    echo No se encontro la tarea "CCTV-Monitor" ^(¿ya estaba desinstalada?^).
) else (
    echo Tarea eliminada correctamente.
)

echo.
echo Nota: esto NO borra el proyecto, el venv, ni tu .env con las llaves.
echo Si quieres borrar todo, hazlo manualmente eliminando esta carpeta.
pause
