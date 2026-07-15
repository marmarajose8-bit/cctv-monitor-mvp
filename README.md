# Monitor CCTV Inteligente — MVP

## Instalación rápida — un solo comando (Windows o Linux)

El proyecto incluye un instalador para cada sistema. Ambos hacen lo mismo:
crean el entorno, instalan dependencias, te piden tus llaves una sola vez,
y dejan el monitor corriendo en segundo plano de forma automática.

### Linux (incluye el contenedor "penguin" de Chromebook/Crostini)
```bash
bash instalar.sh
```
Queda registrado como servicio de usuario `systemd`: arranca solo al iniciar
sesión y se reinicia solo si falla.

**Requisito previo:** ninguno — el script instala `cmake` y las herramientas
de compilación por ti vía `apt` (te pedirá tu contraseña sudo una vez).

Comandos opcionales para revisar el servicio:
```bash
systemctl --user status cctv-monitor      # ver si está corriendo
journalctl --user -u cctv-monitor -f      # ver logs en vivo
systemctl --user stop cctv-monitor        # detenerlo
bash desinstalar.sh                       # quitar el arranque automático
```

### Windows
Doble clic en `instalar.bat` (o ejecutarlo desde CMD/PowerShell).
Queda registrado como Tarea Programada que corre con `pythonw.exe`
**sin ventana de consola visible**, y arranca sola en cada inicio de sesión.

**Requisito previo — este paso SÍ es manual, no se puede automatizar de
forma segura:** instalar una sola vez:
1. [Visual Studio Build Tools (C++)](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. [CMake](https://cmake.org/download/) (marcar "Add CMake to PATH" durante la instalación)

Ambos son necesarios para compilar `dlib`, la librería detrás del
reconocimiento facial. Sin esto, `instalar.bat` fallará en el paso de
`pip install` y te lo va a indicar explícitamente.

Comandos opcionales para revisar la tarea (CMD/PowerShell):
```powershell
schtasks /Query /TN "CCTV-Monitor"        REM ver si está activa
type monitor.log                          REM ver logs
schtasks /End /TN "CCTV-Monitor"          REM detenerla ahora
desinstalar.bat                           REM quitar el arranque automático
```

En ambos casos, lo único manual sea cual sea el sistema operativo es
descargar tu `firebase_credentials.json` desde Firebase Console →
Configuración del proyecto → Cuentas de servicio → Generar nueva clave
privada, y colocarlo en la raíz del proyecto. El instalador te avisa si
falta.

---

## Estructura del proyecto (referencia / instalación manual)


```
cctv_monitor/
├── config.py            # Llaves, Firebase, cuadrantes, umbrales, prompt experto
├── captura.py            # Captura de pantalla + detección de cambios (ahorro de cuota)
├── reconocimiento.py     # Rostros locales + aprendizaje adaptativo en Firebase
├── analisis_ia.py        # Rotador de 5 llaves Gemini + envío de prompt experto
├── main.py                # Orquestador del ciclo completo
├── requirements.txt
└── .env                   # (crear manualmente, no versionar) llaves y credenciales
```

## 1. Instalación de dependencias

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y cmake build-essential python3-dev libopenblas-dev liblapack-dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows
1. Instalar [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (necesario para compilar `dlib`).
2. Instalar [CMake](https://cmake.org/download/) y agregarlo al PATH.
3. Luego:
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> **Nota:** `dlib` (dependencia de `face_recognition`) es la parte más sensible de instalar
> en Windows. Si falla la compilación, usar un wheel precompilado correspondiente a tu
> versión exacta de Python (ej. buscar "dlib whl cp311 win_amd64").

## 2. Configuración

Crear un archivo `.env` en la raíz del proyecto:

```env
GEMINI_KEY_1=AIza...
GEMINI_KEY_2=AIza...
GEMINI_KEY_3=AIza...
GEMINI_KEY_4=AIza...
GEMINI_KEY_5=AIza...

FIREBASE_CRED_PATH=firebase_credentials.json
FIREBASE_DB_URL=https://tu-proyecto.firebaseio.com
FIREBASE_STORAGE_BUCKET=tu-proyecto.appspot.com

CAPTURE_INTERVAL=300
LOG_FILE_PATH=monitor.log
```

Descargar el JSON de credenciales de servicio de Firebase (Project Settings ->
Service Accounts -> Generate new private key) y guardarlo como
`firebase_credentials.json` en la raíz del proyecto.

Ajustar `CAMERA_QUADRANTS` en `config.py` con las coordenadas reales de cada
cámara/cuadrícula según el layout del software de CCTV que se está monitoreando
(puede variarse por cliente/instalación).

## 3. Ejecución en modo "invisible" (background)

### Windows — sin consola visible
```powershell
pythonw.exe main.py
```
`pythonw.exe` ejecuta el script sin abrir ventana de terminal. Para que arranque
junto con el sistema, registrarlo como tarea programada (Task Scheduler) o como
Servicio de Windows usando `pywin32` o la herramienta NSSM.

### Linux — como servicio systemd
Crear `/etc/systemd/system/cctv-monitor.service`:
```ini
[Unit]
Description=Monitor CCTV Inteligente
After=network.target

[Service]
WorkingDirectory=/ruta/al/proyecto/cctv_monitor
ExecStart=/ruta/al/proyecto/cctv_monitor/venv/bin/python3 main.py
Restart=always
User=tu_usuario

[Install]
WantedBy=multi-user.target
```
Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cctv-monitor
sudo systemctl start cctv-monitor
```

## 4. Notas de arquitectura y siguientes pasos para producción

- **Multiprocesamiento por zona:** el MVP procesa cuadrantes secuencialmente;
  para escalar a más cámaras, paralelizar con `concurrent.futures.ThreadPoolExecutor`
  ya que las llamadas a Gemini son I/O-bound.
- **Vinculación evento↔persona:** en `main.py`, el cruce entre el evento detectado
  por la IA y el `subject_id` facial está simplificado (`"por_determinar"`). En
  producción conviene correlacionar por bounding box / timestamp para asociar
  el evento exactamente con el rostro implicado.
- **Cumplimiento normativo:** el uso de reconocimiento facial de personal implica
  datos biométricos. Se recomienda documentar la política de privacidad, obtener
  consentimiento/aviso conforme a la legislación local (GDPR, leyes de habeas data,
  BIPA u otras según el país) antes de desplegar comercialmente.
- **Seguridad de credenciales:** nunca commitear `.env` ni `firebase_credentials.json`
  al repositorio; usar `.gitignore` y, en despliegue real, un gestor de secretos.
- **Reglas de seguridad de Firebase:** configurar Realtime Database Rules y Storage
  Rules para que solo el backend (con credenciales de servicio) pueda escribir,
  y los operadores autenticados solo puedan leer lo que su rol permite.
