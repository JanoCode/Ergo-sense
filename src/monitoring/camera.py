import logging
import threading
from typing import Optional

import cv2
import numpy as np


logger = logging.getLogger(__name__)


class CameraService:
    """Owns a single VideoCapture and selects the first usable camera."""

    def __init__(self, camera_index=0, fallback_indices=(1, 2)):
        self.camera_index = camera_index
        self.fallback_indices = tuple(fallback_indices)
        self.selected_index: Optional[int] = None
        self.cap = None
        self._is_running = False
        self._lock = threading.Lock()

    def _candidate_indices(self):
        return tuple(dict.fromkeys((self.camera_index, 0, *self.fallback_indices)))

    def start(self) -> bool:
        with self._lock:
            if self._is_running and self.cap is not None:
                return True

            for index in self._candidate_indices():
                logger.info("Trying camera index %s", index)
                capture = cv2.VideoCapture(index)
                if not capture.isOpened():
                    logger.warning("Camera index %s is not available", index)
                    capture.release()
                    continue

                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap = capture
                self.selected_index = index
                self._is_running = True
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
                logger.info(
                    "Camera opened successfully: index=%s resolution=%sx%s fps=%.1f",
                    index, width, height, fps,
                )
                return True

            self.cap = None
            self.selected_index = None
            self._is_running = False
            logger.error(
                "No camera available at indices %s",
                self._candidate_indices(),
            )
            return False

    def stop(self):
        with self._lock:
            capture = self.cap
            camera_index = self.selected_index
            self.cap = None
            self.selected_index = None
            self._is_running = False
        if capture is not None:
            capture.release()
            logger.info("Camera %s released", camera_index)

    def get_frame(self) -> Optional[np.ndarray]:
        capture = self.cap
        if not self._is_running or capture is None:
            return None

        success, frame = capture.read()
        if not success or frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def is_running(self) -> bool:
        return self._is_running

    def properties(self):
        capture = self.cap
        if capture is None:
            return self.selected_index, 0, 0, 0.0
        return (
            self.selected_index,
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            float(capture.get(cv2.CAP_PROP_FPS) or 0.0),
        )
