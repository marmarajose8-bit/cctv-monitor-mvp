#!/bin/bash
# =============================================================
# instalar.sh — Instalador único del Monitor CCTV Inteligente
# =============================================================
# Uso: correr UNA sola vez con  ->  bash instalar.sh
#
# Qué hace:
#   1. Crea el entorno virtual e instala dependencias.
#   2. Te pide interactivamente tus llaves/credenciales y arma el .env
#      (solo si no existe todavía, para no pisar uno ya configurado).
#   3. Registra el monitor como servicio de usuario systemd:
#      arranca solo al encender la sesión, se reinicia si falla,
#      y corre en segundo plano sin terminal abierta.
#
# Después de esto, YA NO NECESITAS TERMINAL para el día a día.
# Para ver logs o controlarlo, se dejan al final unos comandos opcionales.
# =============================================================

set -e

PROYECTO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROYECTO_DIR/venv"
SERVICE_NAME="cctv-monitor"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/${SERVICE_NAME}.service"

echo "============================================="
echo " Instalador del Monitor CCTV Inteligente"
echo "============================================="
echo "Proyecto detectado en: $PROYECTO_DIR"
echo ""

# ---------- 1. Dependencias del sistema (compilación de dlib) ----------
echo "[1/5] Verificando dependencias del sistema (puede pedir tu contraseña sudo)..."
sudo apt update -qq
sudo apt install -y -qq cmake build-essential python3-dev python3-venv \
    libopenblas-dev liblapack-dev > /dev/null

# ---------- 2. Entorno virtual ----------
echo "[2/5] Creando entorno virtual e instalando librerías de Python..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$PROYECTO_DIR/requirements.txt" -q
deactivate
echo "    Listo. Esto puede tardar varios minutos la primera vez (dlib compila desde código)."

# ---------- 3. Configuración (.env) ----------
ENV_FILE="$PROYECTO_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "[3/5] Ya existe un .env, no se sobreescribe."
else
    echo "[3/5] Vamos a configurar tus credenciales (solo se guardan en tu máquina, nunca se suben a git)."
    read -rp "  Llave Gemini 1: " GK1
    read -rp "  Llave Gemini 2 (Enter para omitir): " GK2
    read -rp "  Llave Gemini 3 (Enter para omitir): " GK3
    read -rp "  Llave Gemini 4 (Enter para omitir): " GK4
    read -rp "  Llave Gemini 5 (Enter para omitir): " GK5
    read -rp "  URL de Firebase Realtime Database (ej: https://tu-proyecto.firebaseio.com): " FDB
    read -rp "  Storage Bucket de Firebase (ej: tu-proyecto.appspot.com): " FBUCKET
    read -rp "  Intervalo de captura en segundos [300]: " CAPINT
    CAPINT=${CAPINT:-300}

    cat > "$ENV_FILE" <<EOF
GEMINI_KEY_1=$GK1
GEMINI_KEY_2=$GK2
GEMINI_KEY_3=$GK3
GEMINI_KEY_4=$GK4
GEMINI_KEY_5=$GK5

FIREBASE_CRED_PATH=$PROYECTO_DIR/firebase_credentials.json
FIREBASE_DB_URL=$FDB
FIREBASE_STORAGE_BUCKET=$FBUCKET

CAPTURE_INTERVAL=$CAPINT
LOG_FILE_PATH=$PROYECTO_DIR/monitor.log
EOF
    echo "    .env creado en $ENV_FILE"

    if [ ! -f "$PROYECTO_DIR/firebase_credentials.json" ]; then
        echo ""
        echo "    ATENCIÓN: falta el archivo firebase_credentials.json"
        echo "    Descárgalo desde Firebase Console -> Configuración del proyecto ->"
        echo "    Cuentas de servicio -> Generar nueva clave privada, y colócalo en:"
        echo "    $PROYECTO_DIR/firebase_credentials.json"
        echo "    (El servicio no arrancará correctamente hasta que este archivo exista)."
    fi
fi

# ---------- 4. Servicio systemd de usuario ----------
echo "[4/5] Registrando servicio de arranque automático..."
mkdir -p "$SERVICE_DIR"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Monitor CCTV Inteligente
After=network.target

[Service]
WorkingDirectory=$PROYECTO_DIR
ExecStart=$VENV_DIR/bin/python3 $PROYECTO_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
# "Lingering" permite que el servicio siga corriendo aunque cierres sesión
loginctl enable-linger "$USER" 2>/dev/null || true

# ---------- 5. Arranque ----------
echo "[5/5] Iniciando el servicio..."
systemctl --user restart "$SERVICE_NAME"

echo ""
echo "============================================="
echo " Instalación completa."
echo " El monitor ya está corriendo en segundo plano"
echo " y arrancará solo cada vez que inicies sesión."
echo "============================================="
echo ""
echo "Comandos útiles (opcionales, solo si quieres revisar algo):"
echo "  Ver estado:     systemctl --user status $SERVICE_NAME"
echo "  Ver logs vivos: journalctl --user -u $SERVICE_NAME -f"
echo "  Detenerlo:      systemctl --user stop $SERVICE_NAME"
echo "  Reiniciarlo:    systemctl --user restart $SERVICE_NAME"
