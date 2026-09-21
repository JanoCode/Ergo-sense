import math
import numpy as np
import cv2
from typing import Optional
from monitoring.models import FaceLandmarksResult, Point3D
from fatigue.models import HeadPoseAngles, HeadPoseResult

# Puntos 3D del modelo de cabeza (espacio canónico en mm aprox.)
_MODEL_POINTS = np.array([
    (0.0,    0.0,    0.0),       # Nariz (4)
    (0.0,   -63.6, -12.5),       # Mentón (152)
    (-43.3,  32.7, -26.0),       # Esquina ojo izq (33)
    (43.3,   32.7, -26.0),       # Esquina ojo der (263)
    (-28.9, -28.9, -24.1),       # Comisura boca izq (61)
    (28.9,  -28.9, -24.1),       # Comisura boca der (291)
], dtype=np.float64)

# Índices de MediaPipe correspondientes
_LANDMARK_INDICES = [4, 152, 33, 263, 61, 291]

class HeadPoseConfig:
    SUSTAINED_SECONDS = 3.0         # Segundos sostenidos para considerar evento
    DOWN_PITCH_THRESHOLD = 15.0     # Grados hacia abajo
    DEVIATION_THRESHOLD = 20.0      # Grados de desviación de referencia

class HeadPoseEstimator:
    def __init__(self, config: HeadPoseConfig = HeadPoseConfig()):
        self.config = config
        self._reference: Optional[HeadPoseAngles] = None
        self._stable_frames = 0
        self._required_stable_frames = 30

        # Seguimiento de eventos sostenidos
        self._down_tilt_start: Optional[float] = None
        self._deviation_start: Optional[float] = None

    def reset(self):
        self._reference = None
        self._stable_frames = 0
        self._down_tilt_start = None
        self._deviation_start = None

    def _compute_angles(
        self, landmarks: FaceLandmarksResult, frame_width: int, frame_height: int
    ) -> Optional[HeadPoseAngles]:
        if len(landmarks.all_points) < 468:
            return None

        pts = landmarks.all_points
        image_points = np.array([
            (pts[i].x * frame_width, pts[i].y * frame_height)
            for i in _LANDMARK_INDICES
        ], dtype=np.float64)

        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        success, rvec, tvec = cv2.solvePnP(
            _MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return None

        rmat, _ = cv2.Rodrigues(rvec)
        # Descomponer en ángulos de Euler (pitch, yaw, roll)
        sy = math.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
        singular = sy < 1e-6
        if not singular:
            pitch = math.degrees(math.atan2(rmat[2, 1], rmat[2, 2]))
            yaw   = math.degrees(math.atan2(-rmat[2, 0], sy))
            roll  = math.degrees(math.atan2(rmat[1, 0], rmat[0, 0]))
        else:
            pitch = math.degrees(math.atan2(-rmat[1, 2], rmat[1, 1]))
            yaw   = math.degrees(math.atan2(-rmat[2, 0], sy))
            roll  = 0.0

        return HeadPoseAngles(pitch=pitch, yaw=yaw, roll=roll)

    def _angle_deviation(self, a: HeadPoseAngles, b: HeadPoseAngles) -> HeadPoseAngles:
        return HeadPoseAngles(
            pitch=a.pitch - b.pitch,
            yaw=a.yaw - b.yaw,
            roll=a.roll - b.roll
        )

    def _total_deviation(self, dev: HeadPoseAngles) -> float:
        return math.sqrt(dev.pitch**2 + dev.yaw**2 + dev.roll**2)

    def process(
        self,
        landmarks: Optional[FaceLandmarksResult],
        frame_width: int,
        frame_height: int,
        current_time: float
    ) -> HeadPoseResult:
        if not landmarks:
            self._stable_frames = 0
            return HeadPoseResult(None, None, self._reference is not None, False, False)

        angles = self._compute_angles(landmarks, frame_width, frame_height)
        if angles is None:
            self._stable_frames = 0
            return HeadPoseResult(None, None, self._reference is not None, False, False)

        # Intentar calibrar referencia automáticamente
        if self._reference is None:
            self._stable_frames += 1
            if self._stable_frames >= self._required_stable_frames:
                self._reference = angles
        
        deviation = None
        sustained_down = False
        sustained_dev = False

        if self._reference is not None:
            deviation = self._angle_deviation(angles, self._reference)
            total_dev = self._total_deviation(deviation)

            # Detectar inclinación hacia abajo sostenida
            if angles.pitch < -self.config.DOWN_PITCH_THRESHOLD:
                if self._down_tilt_start is None:
                    self._down_tilt_start = current_time
                elif current_time - self._down_tilt_start >= self.config.SUSTAINED_SECONDS:
                    sustained_down = True
            else:
                self._down_tilt_start = None

            # Detectar desviación sostenida de la referencia
            if total_dev > self.config.DEVIATION_THRESHOLD:
                if self._deviation_start is None:
                    self._deviation_start = current_time
                elif current_time - self._deviation_start >= self.config.SUSTAINED_SECONDS:
                    sustained_dev = True
            else:
                self._deviation_start = None

        return HeadPoseResult(
            angles=angles,
            deviation_from_reference=deviation,
            has_reference=self._reference is not None,
            sustained_down_tilt=sustained_down,
            sustained_deviation=sustained_dev
        )
