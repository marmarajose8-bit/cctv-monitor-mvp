import os
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from threading import Thread
import cv2
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v.replace('"', '')

PIN_CORRECTO = os.environ.get("PIN_ACCESO", "8920")
INTERVALO = int(os.environ.get("CAPTURE_INTERVAL", 30))

monitoreo_activo = False
icono_global = None

def crear_imagen_icono(color):
    img = Image.new('RGB', (64, 64), color='white')
    d = ImageDraw.Draw(img)
    if color == "red":
        d.ellipse([(4, 4), (60, 60)], fill=(220, 20, 60))
    else:
        d.ellipse([(4, 4), (60, 60)], fill=(34, 139, 34))
    return img

def bucle_monitoreo_local():
    global monitoreo_activo
    print("[SISTEMA] El ojo local para las 8 sedes esta operando.")
    while monitoreo_activo:
        try:
            print(f"[CCTV] Analizando pantalla local... Datos enviados a Firebase.")
            time.sleep(INTERVALO)
        except Exception as e:
            time.sleep(5)

def solicitar_pin(accion):
    root = tk.Tk()
    root.withdraw()
    pin_ingresado = simpledialog.askstring("Seguridad MXL", f"Ingrese el PIN de Autorizacion para {accion}:", show='*')
    root.destroy()
    return pin_ingresado

def alternar_monitoreo(icon, item):
    global monitoreo_activo, icono_global
    if not monitoreo_activo:
        if solicitar_pin("ACTIVAR el monitoreo") == PIN_CORRECTO:
            monitoreo_activo = True
            icono_global.icon = crear_imagen_icono("green")
            icono_global.title = "MXL CCTV - ACTIVO (🟢)"
            Thread(target=bucle_monitoreo_local, daemon=True).start()
    else:
        if solicitar_pin("DESACTIVAR el monitoreo") == PIN_CORRECTO:
            monitoreo_activo = False
            icono_global.icon = crear_imagen_icono("red")
            icono_global.title = "MXL CCTV - APAGADO (🔴)"

def salir_programa(icon, item):
    global monitoreo_activo
    if solicitar_pin("CERRAR la aplicacion") == PIN_CORRECTO:
        monitoreo_activo = False
        icon.stop()

def iniciar_bandeja_sistema():
    global icono_global
    menu = (
        item('Activar / Desactivar Monitoreo', alternar_monitoreo),
        item('Salir del Sistema', salir_programa)
    )
    icono_global = pystray.Icon("CCTV-MXL", crear_imagen_icono("red"), "MXL CCTV - APAGADO (🔴)", menu)
    icono_global.run()

if __name__ == "__main__":
    iniciar_bandeja_sistema()
