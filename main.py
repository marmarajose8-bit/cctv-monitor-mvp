"""
main.py
-------
Orquestador principal. Ejecuta el ciclo:
Captura -> Filtro de cambios -> Análisis IA -> Reconocimiento facial -> Firebase

Diseñado para correr en segundo plano sin consola gráfica:
- Windows: ejecutar con `pythonw.exe main.py` (no abre ventana de consola),
  o registrar como Servicio de Windows con NSSM / pywin32.
- Linux: ejecutar como servicio systemd o con `nohup python3 main.py &`.
"""

import io
import logging
import time

import numpy as np

import config
from captura import ScreenCapture
from analisis_ia import AnalizadorIA
from reconocimiento import FirebaseManager, ReconocimientoFacial
from control_acceso import ControlAcceso

logging.basicConfig(
    filename=config.LOG_FILE_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


class MonitorOrquestador:
    def __init__(self):
        self.captura = ScreenCapture()
        self.ia = AnalizadorIA()
        self.firebase = FirebaseManager()
        self.reconocimiento = ReconocimientoFacial(self.firebase)
        self.control = ControlAcceso(self.firebase)

    def ciclo(self):
        zonas_con_cambio = self.captura.get_changed_quadrants()

        if not zonas_con_cambio:
            logger.info("Sin cambios en ninguna zona. Ciclo omitido (ahorro de cuota).")
            return

        # Convertir a PIL para Gemini
        zonas_pil = {
            zona: ScreenCapture.to_pil(img) for zona, img in zonas_con_cambio.items()
        }

        # 1. Análisis IA (eventos de disciplina/operación/anomalía)
        resultados_ia = self.ia.analizar_lote(zonas_pil)

        # 2. Reconocimiento facial por zona (solo donde la IA marcó relevancia,
        #    o siempre, según el nivel de exhaustividad deseado)
        for zona, img_bgr in zonas_con_cambio.items():
            img_pil = ScreenCapture.to_pil(img_bgr)
            rostros = self.reconocimiento.detectar_rostros(np.array(img_pil))

            # Bytes JPEG listos para subir a Storage solo si se dispara una alerta
            buf = io.BytesIO()
            img_pil.save(buf, format="JPEG", quality=90)
            jpeg_bytes = buf.getvalue()

            for _, encoding in rostros:
                clasificacion = self.reconocimiento.procesar_rostro(
                    encoding, zona, image_bgr_bytes=jpeg_bytes
                )
                logger.info(f"[{zona}] Rostro clasificado: {clasificacion}")

        # 3. Cruce de eventos IA con clasificación facial -> registrar incidencias
        for zona, resultado in resultados_ia.items():
            for evento in resultado.get("eventos", []):
                if evento["tipo"] != "normal":
                    logger.info(f"[{zona}] Evento detectado: {evento}")
                    # Aquí se podría enlazar el evento con el subject_id más reciente
                    # de esa zona para registrar la incidencia con nombre asociado.
                    self.reconocimiento.registrar_incidencia_disciplina(
                        subject_id="por_determinar",
                        tipo=evento["tipo"],
                        zona=zona,
                        descripcion=evento["descripcion"],
                        severidad=evento["severidad"],
                    )

    def run_forever(self):
        logger.info("Monitor iniciado en modo background.")
        logger.info(f"Llaves Gemini activas: {len(config.GEMINI_API_KEYS)}")
        logger.info(f"Intervalo de captura: {config.CAPTURE_INTERVAL_SECONDS}s")
        logger.info("Esperando activación manual (PIN) para comenzar a capturar...")

        estaba_activo = None  # para loguear solo cuando cambia el estado

        while True:
            try:
                activo = self.control.esta_activo()

                if activo != estaba_activo:
                    logger.info("Sistema ACTIVADO. Iniciando capturas." if activo
                                else "Sistema INACTIVO. En espera de activación.")
                    estaba_activo = activo

                if activo:
                    self.ciclo()
                    time.sleep(config.CAPTURE_INTERVAL_SECONDS)
                else:
                    # Mientras está desactivado, no se captura nada.
                    # Solo se revisa cada pocos segundos si ya lo activaron.
                    time.sleep(config.CONTROL_POLL_INTERVAL_SECONDS)

            except Exception as e:
                logger.exception(f"Error no controlado en el ciclo: {e}")
                time.sleep(config.CONTROL_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    orquestador = MonitorOrquestador()
    orquestador.run_forever()
