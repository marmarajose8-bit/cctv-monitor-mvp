"""
control_acceso.py
------------------
Interruptor manual del sistema: SOLO la persona con el PIN correcto puede
activar o desactivar el monitoreo. Mientras esté desactivado, main.py no
toma capturas ni analiza nada (ahorra cuota y respeta la regla de "solo
corre cuando yo estoy aquí").

Cada cambio de estado queda registrado en Firebase con fecha/hora, para que
quede prueba de quién y cuándo lo activó o desactivó (por ejemplo, si un
jefe lo activa sin avisar).
"""

import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class ControlAcceso:
    def __init__(self, firebase_manager):
        self.firebase = firebase_manager

    # ---------- Verificación de PIN ----------

    def verificar_pin(self, pin_ingresado: str) -> bool:
        return str(pin_ingresado).strip() == str(config.CONTROL_PIN)

    # ---------- Lectura de estado ----------

    def esta_activo(self) -> bool:
        """Lee el estado actual desde Firebase. Si no existe aún, por defecto
        el sistema arranca INACTIVO (seguridad: nunca capturar sin que
        alguien lo haya prendido explícitamente)."""
        estado = self.firebase.ref(config.DB_PATH_CONTROL_ACCESO).get()
        if not estado:
            return False
        return bool(estado.get("activo", False))

    # ---------- Cambios de estado (requieren PIN) ----------

    def activar(self, pin_ingresado: str, nombre: str = "Responsable") -> bool:
        if not self.verificar_pin(pin_ingresado):
            logger.warning("Intento de ACTIVAR con PIN incorrecto.")
            return False

        self._set_estado(activo=True, nombre=nombre)
        logger.info(f"Monitoreo ACTIVADO por {nombre}.")
        return True

    def desactivar(self, pin_ingresado: str, nombre: str = "Responsable") -> bool:
        if not self.verificar_pin(pin_ingresado):
            logger.warning("Intento de DESACTIVAR con PIN incorrecto.")
            return False

        self._set_estado(activo=False, nombre=nombre)
        logger.info(f"Monitoreo DESACTIVADO por {nombre}.")
        return True

    def _set_estado(self, activo: bool, nombre: str):
        ahora = datetime.utcnow().isoformat()

        self.firebase.ref(config.DB_PATH_CONTROL_ACCESO).set({
            "activo": activo,
            "por": nombre,
            "timestamp": ahora,
        })

        # Historial append-only: nunca se sobreescribe, queda todo el rastro
        self.firebase.ref(config.DB_PATH_CONTROL_HISTORIAL).push({
            "activo": activo,
            "por": nombre,
            "timestamp": ahora,
        })
