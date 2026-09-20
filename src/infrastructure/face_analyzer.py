import mediapipe as mp
import cv2
import numpy as np
from typing import Optional
from domain.facial_landmarks import FaceLandmarksResult, Point3D

class FaceAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Índices de MediaPipe para zonas específicas
        self.LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144, 145, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380, 374, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
        self.MOUTH_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
        # Puntos útiles para pose (nariz, mentón, esquinas de los ojos, extremos de la boca)
        self.HEAD_POSE_INDICES = [1, 152, 33, 263, 61, 291]
        
    def analyze_frame(self, frame_rgb: np.ndarray) -> Optional[FaceLandmarksResult]:
        results = self.face_mesh.process(frame_rgb)
        
        if not results.multi_face_landmarks:
            return None
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        all_points = [Point3D(x=lm.x, y=lm.y, z=lm.z) for lm in landmarks]
        
        left_eye = [all_points[i] for i in self.LEFT_EYE_INDICES]
        right_eye = [all_points[i] for i in self.RIGHT_EYE_INDICES]
        mouth = [all_points[i] for i in self.MOUTH_INDICES]
        head_pose = [all_points[i] for i in self.HEAD_POSE_INDICES]
        
        return FaceLandmarksResult(
            left_eye=left_eye,
            right_eye=right_eye,
            mouth=mouth,
            head_orientation_points=head_pose,
            all_points=all_points
        )

    def draw_landmarks(self, frame_rgb: np.ndarray, result: FaceLandmarksResult) -> np.ndarray:
        frame_out = frame_rgb.copy()
        h, w, _ = frame_out.shape
        
        def draw_points(points, color):
            for p in points:
                cx, cy = int(p.x * w), int(p.y * h)
                cv2.circle(frame_out, (cx, cy), 1, color, -1)
                
        draw_points(result.left_eye, (0, 255, 0))    # Verde
        draw_points(result.right_eye, (0, 255, 0))   # Verde
        draw_points(result.mouth, (255, 0, 0))       # Azul oscuro
        draw_points(result.head_orientation_points, (0, 0, 255)) # Rojo
        
        return frame_out
