"""
captura.py
----------
Responsable de:
1. Tomar capturas de pantalla internas de la PC de monitoreo (sin abrir ventanas).
2. Recortar los cuadrantes definidos en config.CAMERA_QUADRANTS.
3. Detectar si hubo cambio real respecto a la captura anterior (por cuadrante),
   para evitar enviar imágenes estáticas a la IA y así ahorrar cuota de API.
"""

import logging
import numpy as np
import cv2
import mss
from PIL import Image

import config

logger = logging.getLogger(__name__)


class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()
        # Guarda el último frame (en escala de grises, reducido) por cada cuadrante
        self._last_frames = {}

    def take_full_screenshot(self) -> np.ndarray:
        """Toma una captura de pantalla completa (todos los monitores fusionados
        o el monitor principal, según configuración de mss) y la retorna como
        array numpy en formato BGR (compatible con OpenCV)."""
        monitor = self.sct.monitors[1]  # 0 = todos, 1 = monitor principal
        shot = self.sct.grab(monitor)
        img = np.array(shot)  # BGRA
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def crop_quadrants(self, full_image: np.ndarray) -> dict:
        """Recorta la imagen completa según los cuadrantes definidos en config.
        Retorna: { "nombre_zona": np.ndarray }"""
        quadrants = {}
        h_img, w_img = full_image.shape[:2]

        for zona, data in config.CAMERA_QUADRANTS.items():
            x, y, w, h = data["coords"]
            # Protección ante desbordes si la resolución cambió
            x2, y2 = min(x + w, w_img), min(y + h, h_img)
            crop = full_image[y:y2, x:x2]
            if crop.size > 0:
                quadrants[zona] = crop
        return quadrants

    def _preprocess_for_diff(self, image: np.ndarray) -> np.ndarray:
        """Reduce resolución y convierte a escala de grises para comparar rápido."""
        small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return gray

    def has_changed(self, zona: str, current_image: np.ndarray) -> bool:
        """
        Compara la imagen actual del cuadrante contra el último frame guardado.
        Usa diferencia absoluta de píxeles (rápido) como filtro local.
        Retorna True si el cambio supera el umbral configurado (justifica
        enviar a la IA), False si la escena está estática.
        """
        current_small = self._preprocess_for_diff(current_image)
        last_small = self._last_frames.get(zona)

        # Primera vez que se ve esta zona: se considera cambio (para tener baseline)
        if last_small is None:
            self._last_frames[zona] = current_small
            return True

        diff = cv2.absdiff(current_small, last_small)
        non_zero_pixels = np.count_nonzero(diff > 25)  # umbral de sensibilidad por pixel
        total_pixels = diff.size
        percent_changed = (non_zero_pixels / total_pixels) * 100

        self._last_frames[zona] = current_small

        changed = percent_changed >= config.MIN_PIXEL_DIFF_PERCENT
        if not changed:
            logger.debug(f"[{zona}] Sin cambios relevantes ({percent_changed:.2f}%). Se omite envío a IA.")
        return changed

    def get_changed_quadrants(self) -> dict:
        """
        Flujo completo: captura pantalla, recorta cuadrantes, filtra solo
        los que tuvieron cambios reales. Retorna dict listo para analizar.
        """
        full = self.take_full_screenshot()
        quadrants = self.crop_quadrants(full)

        changed_quadrants = {}
        for zona, img in quadrants.items():
            if self.has_changed(zona, img):
                changed_quadrants[zona] = img

        return changed_quadrants

    @staticmethod
    def to_pil(image_bgr: np.ndarray) -> Image.Image:
        """Convierte un array BGR (OpenCV) a PIL Image (RGB) para enviar a Gemini."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
