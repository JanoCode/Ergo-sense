from pathlib import Path
import time
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from monitoring.models import FaceLandmarksResult, Point3D


DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "models"
    / "face_landmarker.task"
)


class FaceAnalyzer:
    """Extract facial landmarks with the modern MediaPipe Tasks API."""

    LEFT_EYE_INDICES = [
        33, 160, 158, 133, 153, 144, 145, 154, 155,
        133, 173, 157, 158, 159, 160, 161, 246,
    ]
    RIGHT_EYE_INDICES = [
        362, 385, 387, 263, 373, 380, 374, 381, 382,
        362, 398, 384, 385, 386, 387, 388, 466,
    ]
    MOUTH_INDICES = [
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
        291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95,
    ]
    HEAD_POSE_INDICES = [1, 152, 33, 263, 61, 291]

    def __init__(self, model_path: Optional[Path] = None, landmarker=None):
        self.model_path = Path(model_path or DEFAULT_MODEL_PATH).resolve()
        self._last_timestamp_ms = 0

        if landmarker is not None:
            self.face_landmarker = landmarker
            return

        if not self.model_path.is_file():
            raise FileNotFoundError(
                "No se encontró el modelo de MediaPipe Face Landmarker en "
                f"{self.model_path}. Reinstala el proyecto o restaura el archivo "
                "assets/models/face_landmarker.task."
            )

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(self.model_path)
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.face_landmarker = (
            mp.tasks.vision.FaceLandmarker.create_from_options(options)
        )

    def _next_timestamp_ms(self) -> int:
        timestamp_ms = time.monotonic_ns() // 1_000_000
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def analyze_frame(
        self, frame_rgb: np.ndarray
    ) -> Optional[FaceLandmarksResult]:
        if not isinstance(frame_rgb, np.ndarray) or frame_rgb.ndim != 3:
            return None
        if frame_rgb.shape[2] != 3 or frame_rgb.size == 0:
            return None

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(frame_rgb, dtype=np.uint8),
        )
        results = self.face_landmarker.detect_for_video(
            image, self._next_timestamp_ms()
        )

        if not results.face_landmarks:
            return None

        landmarks = results.face_landmarks[0]
        all_points = [
            Point3D(x=float(lm.x), y=float(lm.y), z=float(lm.z))
            for lm in landmarks
        ]

        required_index = max(
            self.LEFT_EYE_INDICES
            + self.RIGHT_EYE_INDICES
            + self.MOUTH_INDICES
            + self.HEAD_POSE_INDICES
        )
        if len(all_points) <= required_index:
            return None

        return FaceLandmarksResult(
            left_eye=[all_points[i] for i in self.LEFT_EYE_INDICES],
            right_eye=[all_points[i] for i in self.RIGHT_EYE_INDICES],
            mouth=[all_points[i] for i in self.MOUTH_INDICES],
            head_orientation_points=[
                all_points[i] for i in self.HEAD_POSE_INDICES
            ],
            all_points=all_points,
        )

    def draw_landmarks(
        self, frame_rgb: np.ndarray, result: FaceLandmarksResult
    ) -> np.ndarray:
        frame_out = frame_rgb.copy()
        height, width, _ = frame_out.shape

        def draw_points(points, color):
            for point in points:
                center = int(point.x * width), int(point.y * height)
                cv2.circle(frame_out, center, 1, color, -1)

        draw_points(result.left_eye, (0, 255, 0))
        draw_points(result.right_eye, (0, 255, 0))
        draw_points(result.mouth, (255, 0, 0))
        draw_points(result.head_orientation_points, (0, 0, 255))
        return frame_out

    def close(self) -> None:
        landmarker = getattr(self, "face_landmarker", None)
        if landmarker is not None:
            landmarker.close()
            self.face_landmarker = None
