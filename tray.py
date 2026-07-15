"""
tray.py
-------
Ícono en la barra de tareas de Windows (system tray) para prender/apagar
el monitoreo. Pide PIN antes de cualquier cambio de estado.

Correr este archivo por separado de main.py:
  - main.py        -> hace el trabajo pesado (captura, IA, Firebase), se
                       queda dormido/en espera mientras el sistema está
                       desactivado.
  - tray.py         -> corre en la sesión del usuario (necesita escritorio),
                       muestra el ícono, pide el PIN y cambia el estado.

Ambos se conectan al mismo nodo de Firebase, así que no importa cuál
arranque primero.

Instalar dependencias adicionales:
    pip install pystray
(tkinter ya viene incluido con Python en Windows)
"""

import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

from PIL import Image, ImageDraw
import pystray

from reconocimiento import FirebaseManager
from control_acceso import ControlAcceso


def _crear_icono(color: str) -> Image.Image:
    """Genera un ícono circular simple (verde = activo, rojo = inactivo)
    sin depender de ningún archivo de imagen externo."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=color, outline="black", width=2)
    return img


class TrayApp:
    def __init__(self):
        self.firebase = FirebaseManager()
        self.control = ControlAcceso(self.firebase)

        self.icon = pystray.Icon(
            "cctv_monitor",
            _crear_icono("green" if self.control.esta_activo() else "red"),
            self._titulo(),
            menu=self._construir_menu(),
        )

    def _titulo(self) -> str:
        estado = "ACTIVO" if self.control.esta_activo() else "INACTIVO"
        return f"Monitor CCTV — {estado}"

    def _construir_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: "Desactivar monitoreo" if self.control.esta_activo()
                else "Activar monitoreo",
                self._toggle,
            ),
            pystray.MenuItem("Salir", self._salir),
        )

    def _pedir_pin_y_nombre(self):
        """Abre una ventanita simple para pedir PIN. Retorna el PIN o None
        si el usuario canceló."""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        pin = simpledialog.askstring(
            "Monitor CCTV", "PIN de autorización:", show="*", parent=root
        )
        root.destroy()
        return pin

    def _toggle(self, icon, item):
        pin = self._pedir_pin_y_nombre()
        if pin is None:
            return  # Canceló, no hacemos nada

        if self.control.esta_activo():
            ok = self.control.desactivar(pin)
            accion = "desactivado"
        else:
            ok = self.control.activar(pin)
            accion = "activado"

        if ok:
            icon.icon = _crear_icono("green" if self.control.esta_activo() else "red")
            icon.title = self._titulo()
            icon.menu = self._construir_menu()
            icon.notify(f"Monitoreo {accion} correctamente.", "Monitor CCTV")
        else:
            self._notificar_error()

    def _notificar_error(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror("Monitor CCTV", "PIN incorrecto. No se realizó el cambio.")
        root.destroy()

    def _salir(self, icon, item):
        icon.stop()

    def run(self):
        self.icon.run()


if __name__ == "__main__":
    TrayApp().run()
