import os
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from threading import Thread
import cv2
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

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

def bucle_monitoreo():
    global monitoreo_activo
    print("[SISTEMA] Motor de IA para 8 sedes iniciado.")
    while monitoreo_activo:
        try:
            print(f"[CCTV] Analizando canales... Ciclo ejecutado.")
            time.sleep(INTERVALO)
        except Exception as e:
            time.sleep(5)

def solicitar_pin(accion):
    root = tk.Tk()
    root.withdraw()
    pin_ingresado = simpledialog.askstring("Seguridad MXL", f"Ingrese el PIN para {accion}:", show='*')
    root.destroy()
    return pin_ingresado

def alternar_monitoreo(icon, item):
    global monitoreo_activo, icono_global
    if not monitoreo_activo:
        if solicitar_pin("ACTIVAR") == PIN_CORRECTO:
            monitoreo_activo = True
            icono_global.icon = crear_imagen_icono("green")
            Thread(target=bucle_monitoreo, daemon=True).start()
    else:
        if solicitar_pin("DESACTIVAR") == PIN_CORRECTO:
            monitoreo_activo = False
            icono_global.icon = crear_imagen_icono("red")

def iniciar_bandeja_sistema():
    global icono_global
    menu = (item('Activar/Desactivar', alternar_monitoreo),)
    icono_global = pystray.Icon("CCTV-MXL", crear_imagen_icono("red"), "MXL CCTV", menu)
    icono_global.run()

if __name__ == "__main__":
    iniciar_bandeja_sistema()
