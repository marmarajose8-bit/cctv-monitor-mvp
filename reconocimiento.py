"""
reconocimiento.py
------------------
Responsable de:
1. Detección facial local (face_recognition / dlib).
2. Fase de Observación: registrar sujetos temporales y rastrear su recurrencia.
3. Fase de Alerta: promover a "Personal Habitual" o disparar "Alerta de Intruso".
4. Toda la persistencia (whitelist, temporales, incidencias, fotos) vive en Firebase.
"""

import io
import logging
import uuid
from datetime import datetime, timedelta

import face_recognition
import numpy as np
import firebase_admin
from firebase_admin import credentials, db, storage

import config

logger = logging.getLogger(__name__)


class FirebaseManager:
    """Encapsula la conexión e inicialización única de Firebase."""

    _initialized = False

    def __init__(self):
        if not FirebaseManager._initialized:
            cred = credentials.Certificate(config.FIREBASE_CONFIG["credentials_path"])
            firebase_admin.initialize_app(cred, {
                "databaseURL": config.FIREBASE_CONFIG["databaseURL"],
                "storageBucket": config.FIREBASE_CONFIG["storageBucket"],
            })
            FirebaseManager._initialized = True

        self.bucket = storage.bucket()

    def ref(self, path: str):
        return db.reference(path)


class ReconocimientoFacial:
    """
    Gestiona el ciclo de vida de identidades:
    Rostro nuevo -> Sujeto_Temporal -> (si es recurrente y normal) -> Personal_Habitual
    Rostro no identificado en zona crítica -> Alerta_Intruso inmediata
    """

    def __init__(self, firebase: FirebaseManager):
        self.firebase = firebase
        self._habitual_cache = {}   # {subject_id: encoding} cargado en memoria al iniciar
        self._temporal_cache = {}   # {subject_id: encoding}
        self._load_known_faces()

    # ---------- Carga inicial desde Firebase ----------

    def _load_known_faces(self):
        habitual = self.firebase.ref(config.DB_PATH_PERSONAL_HABITUAL).get() or {}
        for subject_id, data in habitual.items():
            if "encoding" in data:
                self._habitual_cache[subject_id] = np.array(data["encoding"])

        temporales = self.firebase.ref(config.DB_PATH_SUJETOS_TEMPORALES).get() or {}
        for subject_id, data in temporales.items():
            if "encoding" in data:
                self._temporal_cache[subject_id] = np.array(data["encoding"])

        logger.info(f"Cargados {len(self._habitual_cache)} habituales y "
                    f"{len(self._temporal_cache)} temporales desde Firebase.")

    # ---------- Detección ----------

    def detectar_rostros(self, image_rgb: np.ndarray):
        """Retorna lista de (ubicacion, encoding) por cada rostro detectado."""
        locations = face_recognition.face_locations(image_rgb, model="hog")  # "cnn" si hay GPU
        encodings = face_recognition.face_encodings(image_rgb, locations)
        return list(zip(locations, encodings))

    def _buscar_coincidencia(self, encoding, cache: dict):
        if not cache:
            return None
        ids = list(cache.keys())
        known_encodings = list(cache.values())
        matches = face_recognition.compare_faces(
            known_encodings, encoding, tolerance=config.FACE_MATCH_TOLERANCE
        )
        distances = face_recognition.face_distance(known_encodings, encoding)
        if True in matches:
            best_idx = int(np.argmin(distances))
            if matches[best_idx]:
                return ids[best_idx]
        return None

    # ---------- Lógica principal por rostro detectado ----------

    def procesar_rostro(self, encoding: np.ndarray, zona: str, image_bgr_bytes: bytes = None):
        """
        Determina si el rostro es Personal Habitual, Sujeto Temporal recurrente,
        o un Intruso desconocido. Aplica la lógica de la Fase de Aprendizaje.
        Retorna un dict con el resultado de la clasificación.
        """
        # 1. ¿Es personal habitual?
        habitual_id = self._buscar_coincidencia(encoding, self._habitual_cache)
        if habitual_id:
            self._registrar_presencia(config.DB_PATH_PERSONAL_HABITUAL, habitual_id)
            return {"clasificacion": "habitual", "subject_id": habitual_id}

        # 2. ¿Es un sujeto temporal ya conocido?
        temporal_id = self._buscar_coincidencia(encoding, self._temporal_cache)
        if temporal_id:
            dias_recurrentes = self._registrar_presencia(
                config.DB_PATH_SUJETOS_TEMPORALES, temporal_id
            )
            if dias_recurrentes >= config.RECURRENCE_DAYS_FOR_WHITELIST:
                self._promover_a_habitual(temporal_id, encoding)
                return {"clasificacion": "habitual", "subject_id": temporal_id, "promovido": True}
            return {"clasificacion": "temporal", "subject_id": temporal_id}

        # 3. Rostro completamente nuevo
        if zona in config.CRITICAL_ZONES:
            # Zona crítica + desconocido total = Alerta de Intruso inmediata
            subject_id = f"Intruso_{uuid.uuid4().hex[:8]}"
            self._disparar_alerta_intruso(subject_id, zona, encoding, image_bgr_bytes)
            return {"clasificacion": "intruso", "subject_id": subject_id}
        else:
            # Zona no crítica: se registra como temporal para observación
            subject_id = self._registrar_sujeto_temporal(encoding)
            return {"clasificacion": "temporal_nuevo", "subject_id": subject_id}

    # ---------- Persistencia en Firebase ----------

    def _registrar_sujeto_temporal(self, encoding: np.ndarray) -> str:
        subject_id = f"Sujeto_Temporal_{uuid.uuid4().hex[:6]}"
        self._temporal_cache[subject_id] = encoding
        self.firebase.ref(f"{config.DB_PATH_SUJETOS_TEMPORALES}/{subject_id}").set({
            "encoding": encoding.tolist(),
            "primera_deteccion": datetime.utcnow().isoformat(),
            "dias_vistos": [datetime.utcnow().strftime("%Y-%m-%d")],
        })
        return subject_id

    def _registrar_presencia(self, path: str, subject_id: str) -> int:
        """Añade el día de hoy a la lista de días vistos si no está ya. Retorna
        el total de días distintos registrados (para evaluar recurrencia)."""
        ref = self.firebase.ref(f"{path}/{subject_id}/dias_vistos")
        dias = ref.get() or []
        hoy = datetime.utcnow().strftime("%Y-%m-%d")
        if hoy not in dias:
            dias.append(hoy)
            ref.set(dias)
        return len(dias)

    def _promover_a_habitual(self, subject_id: str, encoding: np.ndarray):
        data = self.firebase.ref(f"{config.DB_PATH_SUJETOS_TEMPORALES}/{subject_id}").get() or {}
        self.firebase.ref(f"{config.DB_PATH_PERSONAL_HABITUAL}/{subject_id}").set({
            "encoding": encoding.tolist(),
            "dias_vistos": data.get("dias_vistos", []),
            "promovido_el": datetime.utcnow().isoformat(),
        })
        self._habitual_cache[subject_id] = encoding
        self._temporal_cache.pop(subject_id, None)
        self.firebase.ref(f"{config.DB_PATH_SUJETOS_TEMPORALES}/{subject_id}").delete()
        logger.info(f"{subject_id} promovido a Personal Habitual tras "
                    f"{config.RECURRENCE_DAYS_FOR_WHITELIST} días de recurrencia normal.")

    def _disparar_alerta_intruso(self, subject_id: str, zona: str,
                                  encoding: np.ndarray, image_bytes: bytes):
        foto_url = None
        if image_bytes:
            blob_path = f"alertas_intruso/{subject_id}.jpg"
            blob = self.firebase.bucket.blob(blob_path)
            blob.upload_from_string(image_bytes, content_type="image/jpeg")
            blob.make_public()  # o usar signed URL si se requiere control de acceso
            foto_url = blob.public_url

        self.firebase.ref(f"{config.DB_PATH_ALERTAS_INTRUSO}/{subject_id}").set({
            "zona": zona,
            "timestamp": datetime.utcnow().isoformat(),
            "foto_url": foto_url,
            "estado": "sin_revisar",
        })
        logger.warning(f"ALERTA DE INTRUSO disparada: {subject_id} en zona crítica '{zona}'.")

    def registrar_incidencia_disciplina(self, subject_id: str, tipo: str,
                                         zona: str, descripcion: str, severidad: str):
        """Registra novedad de control interno para Personal Habitual (discreto,
        no dispara alerta inmediata como el intruso)."""
        incidencia_id = f"{tipo}_{uuid.uuid4().hex[:6]}"
        self.firebase.ref(f"{config.DB_PATH_INCIDENCIAS}/{incidencia_id}").set({
            "subject_id": subject_id,
            "tipo": tipo,
            "zona": zona,
            "descripcion": descripcion,
            "severidad": severidad,
            "timestamp": datetime.utcnow().isoformat(),
        })
