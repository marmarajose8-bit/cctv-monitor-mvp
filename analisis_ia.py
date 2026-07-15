"""
analisis_ia.py
--------------
Responsable de:
1. Balanceo Round-Robin entre hasta 5 llaves de Gemini API (evita rate-limit).
2. Envío de imágenes + system instruction experto en CCTV.
3. Parseo de la respuesta estructurada (JSON) para pasarla al orquestador.
"""

import io
import json
import logging
import time
from itertools import cycle

import google.generativeai as genai
from PIL import Image

import config

logger = logging.getLogger(__name__)


class GeminiKeyRotator:
    """
    Round-Robin simple: cada llamada consecutiva usa la siguiente llave
    de la lista. Con 5 llaves y un intervalo de captura de 5 min, cada
    llave individual descansa entre 15 y 25 minutos antes de reutilizarse.
    """

    def __init__(self, api_keys: list):
        if not api_keys:
            raise ValueError("No hay llaves de Gemini configuradas en config.py")
        self._keys = api_keys
        self._cycle = cycle(api_keys)
        # Registro simple de última vez que se usó cada llave (para métricas/logs)
        self._last_used = {k: None for k in api_keys}

    def get_next_key(self) -> str:
        key = next(self._cycle)
        self._last_used[key] = time.time()
        return key

    def total_keys(self) -> int:
        return len(self._keys)


class AnalizadorIA:
    def __init__(self):
        self.rotator = GeminiKeyRotator(config.GEMINI_API_KEYS)

    def _pil_to_bytes(self, image: Image.Image) -> bytes:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    def analizar_zona(self, zona: str, image: Image.Image, reintentos: int = None) -> dict:
        """
        Envía una imagen de una zona/cuadrante a Gemini con el prompt experto.
        Si una llave falla (cuota agotada, error de red), reintenta automáticamente
        con la siguiente llave del rotador, hasta agotar el número de llaves disponibles.
        Retorna el JSON parseado con la lista de eventos detectados.
        """
        max_intentos = reintentos or self.rotator.total_keys()
        ultimo_error = None

        for intento in range(max_intentos):
            api_key = self.rotator.get_next_key()
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name=config.GEMINI_MODEL,
                    system_instruction=config.SYSTEM_INSTRUCTION_PROMPT,
                )

                prompt = f"Analiza la siguiente imagen correspondiente a la zona: '{zona}'."
                response = model.generate_content(
                    [prompt, image],
                    generation_config={"response_mime_type": "application/json"},
                )

                resultado = json.loads(response.text)
                logger.debug(f"[{zona}] Análisis OK con llave índice {intento}.")
                return resultado

            except Exception as e:
                ultimo_error = e
                logger.warning(f"[{zona}] Falló llave (intento {intento + 1}/{max_intentos}): {e}. "
                                f"Rotando a la siguiente llave...")
                continue

        logger.error(f"[{zona}] Todas las llaves fallaron. Último error: {ultimo_error}")
        return {"eventos": [], "error": str(ultimo_error)}

    def analizar_lote(self, quadrants_pil: dict) -> dict:
        """
        Recibe { "zona": PIL.Image, ... } (ya filtrado por captura.py para solo
        incluir zonas con cambios reales) y retorna { "zona": resultado_json }.
        """
        resultados = {}
        for zona, image in quadrants_pil.items():
            resultados[zona] = self.analizar_zona(zona, image)
        return resultados
