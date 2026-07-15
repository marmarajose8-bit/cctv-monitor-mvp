"""
config.py
---------
Configuración centralizada del sistema. En producción, las llaves y credenciales
NO deben quedar hardcodeadas: usar variables de entorno (.env con python-dotenv)
o un vault de secretos. Aquí se muestran como placeholders para el MVP.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# 1. GEMINI API - SISTEMA ROTATIVO (hasta 5 llaves)
# =========================================================
GEMINI_API_KEYS = [
    os.getenv("GEMINI_KEY_1", "TU_LLAVE_1"),
    os.getenv("GEMINI_KEY_2", "TU_LLAVE_2"),
    os.getenv("GEMINI_KEY_3", "TU_LLAVE_3"),
    os.getenv("GEMINI_KEY_4", "TU_LLAVE_4"),
    os.getenv("GEMINI_KEY_5", "TU_LLAVE_5"),
]
# Filtra llaves vacías/placeholder para que el rotador solo use las configuradas
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k and not k.startswith("TU_LLAVE")]

GEMINI_MODEL = "gemini-2.0-flash"  # Modelo económico y rápido, ideal para visión + alto volumen

# =========================================================
# 2. FIREBASE
# =========================================================
FIREBASE_CONFIG = {
    "credentials_path": os.getenv("FIREBASE_CRED_PATH", "firebase_credentials.json"),
    "databaseURL": os.getenv("FIREBASE_DB_URL", "https://tu-proyecto.firebaseio.com"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "tu-proyecto.appspot.com"),
}

# Rutas dentro de Realtime Database
DB_PATH_PERSONAL_HABITUAL = "personal_habitual"
DB_PATH_SUJETOS_TEMPORALES = "sujetos_temporales"
DB_PATH_INCIDENCIAS = "incidencias"
DB_PATH_ALERTAS_INTRUSO = "alertas_intruso"

# =========================================================
# 3. CAPTURA Y OPTIMIZACIÓN DE CUOTA
# =========================================================
CAPTURE_INTERVAL_SECONDS = int(os.getenv("CAPTURE_INTERVAL", 300))  # 5 min por defecto
CHANGE_DETECTION_THRESHOLD = 0.98   # % de similitud SSIM bajo el cual se considera "cambio"
MIN_PIXEL_DIFF_PERCENT = 0.5        # % mínimo de píxeles distintos para disparar análisis

# =========================================================
# 4. CUADRANTES DE CÁMARAS EN PANTALLA
# Coordenadas relativas a la captura completa (x, y, ancho, alto) en píxeles.
# Ajustar según el layout real del software de CCTV que se esté monitoreando.
# =========================================================
CAMERA_QUADRANTS = {
    "Recepcion":            {"coords": (0, 0, 640, 360),   "critica": False},
    "Puesto_Caja_01":       {"coords": (640, 0, 640, 360), "critica": False},
    "Zona_Combustible":     {"coords": (0, 360, 640, 360), "critica": True},
    "Parqueo_Perimetral":   {"coords": (640, 360, 640, 360), "critica": True},
}

CRITICAL_ZONES = [name for name, data in CAMERA_QUADRANTS.items() if data["critica"]]

# =========================================================
# 5. UMBRALES DE COMPORTAMIENTO
# =========================================================
DISCIPLINE_THRESHOLD_MINUTES = 5     # Uso de celular sostenido
ABSENCE_THRESHOLD_MINUTES = 5        # Puesto desatendido
RECURRENCE_DAYS_FOR_WHITELIST = 5    # Días de presencia normal para pasar a "Personal Habitual"
FACE_MATCH_TOLERANCE = 0.5           # Tolerancia de face_recognition (menor = más estricto)

# =========================================================
# 6. SYSTEM INSTRUCTION - PERFIL EXPERTO INYECTADO A GEMINI
# =========================================================
SYSTEM_INSTRUCTION_PROMPT = """
Eres un Auditor Senior de CCTV. Tu tarea es analizar de forma preventiva y meticulosa
cada cuadrícula de cámaras. Identifica:

1. Uso de teléfonos celulares o dispositivos de ocio por el personal de la empresa
   por más de 5 minutos (Incidencia de Disciplina).
2. Puestos clave desatendidos, vacíos o abandonados por más de 5 minutos
   (Alerta de Operación).
3. Anomalías físicas graves: personas sospechosas merodeando en áreas críticas como
   combustible/parqueos, obstrucción de cámaras, intrusiones, o cualquier persona
   tomando/manipulando mercancía, herramientas, dinero u objetos de forma indebida
   (posible hurto). Sé objetivo: describe solo lo observado, sin acusar directamente;
   marca "requiere_alerta_inmediata": true cuando sea una situación de alta severidad.

Responde ÚNICAMENTE en formato JSON válido, sin texto adicional, con esta estructura:
{
  "eventos": [
    {
      "tipo": "disciplina|operacion|anomalia|normal",
      "zona": "nombre_de_la_zona",
      "descripcion": "breve descripción objetiva de lo observado",
      "severidad": "baja|media|alta",
      "requiere_alerta_inmediata": true|false
    }
  ]
}
Si no observas ninguna novedad, responde con "eventos": [] y no inventes incidentes.
"""

# =========================================================
# 7. MODO DE EJECUCIÓN
# =========================================================
RUN_HEADLESS = True  # Sin consola gráfica (background service)
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "monitor.log")

# =========================================================
# 8. CONTROL DE ACTIVACIÓN (interruptor manual protegido por PIN)
# =========================================================
# El PIN NUNCA debe quedar en texto plano en un repo público. Aquí se lee
# de variable de entorno; el valor por defecto es el que definió el dueño
# del sistema para uso local/privado.
CONTROL_PIN = os.getenv("CONTROL_PIN", "8920")

DB_PATH_CONTROL_ACCESO = "control_acceso"          # Estado actual (activo/inactivo)
DB_PATH_CONTROL_HISTORIAL = "control_acceso_historial"  # Log de cada cambio

# Cada cuántos segundos main.py vuelve a consultar si sigue activo
# (para reaccionar rápido si se desactiva desde el tray o desde Firebase)
CONTROL_POLL_INTERVAL_SECONDS = 15
