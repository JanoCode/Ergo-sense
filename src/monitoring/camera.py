import cv2
import numpy as np
from typing import Optional

class CameraService:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self._is_running = False

    def start(self) -> bool:
        if self._is_running:
            return True
        
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.cap = None
            return False
            
        self._is_running = True
        return True

    def stop(self):
        self._is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_frame(self) -> Optional[np.ndarray]:
        if not self._is_running or not self.cap:
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        # OpenCV usa BGR, convertimos a RGB para interfaces gráficas
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame_rgb

    def is_running(self) -> bool:
        return self._is_running
