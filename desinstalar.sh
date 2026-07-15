#!/bin/bash
# desinstalar.sh — Quita el servicio del Monitor CCTV Inteligente (Linux)
set -e

SERVICE_NAME="cctv-monitor"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

echo "Deteniendo y deshabilitando el servicio..."
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true

if [ -f "$SERVICE_FILE" ]; then
    rm "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo "Servicio eliminado."
else
    echo "No se encontró el servicio (¿ya estaba desinstalado?)."
fi

echo ""
echo "Nota: esto NO borra el proyecto, el venv, ni tu .env con las llaves."
echo "Si quieres borrar todo, hazlo manualmente eliminando esta carpeta."
