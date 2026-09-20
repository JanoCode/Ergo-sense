import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from domain.metrics import EyeState
from domain.facial_landmarks import FaceLandmarksResult, Point3D
from domain.ear_calculator import calculate_ear_from_points, get_eye_state, EARConfig
from domain.blink_detector import BlinkDetector, BlinkConfig

class TestEyeMetrics(unittest.TestCase):
    def test_calculate_ear(self):
        # Ojo muy abierto (simulado con geometría simple)
        # p1 (0, 0), p4 (10, 0)
        # p2 (2, 2), p6 (2, -2) -> dist = 4
        # p3 (8, 2), p5 (8, -2) -> dist = 4
        # EAR = (4 + 4) / (2 * 10) = 8 / 20 = 0.4
        ear = calculate_ear_from_points(
            Point3D(0, 0, 0),
            Point3D(2, 2, 0),
            Point3D(8, 2, 0),
            Point3D(10, 0, 0),
            Point3D(8, -2, 0),
            Point3D(2, -2, 0)
        )
        self.assertAlmostEqual(ear, 0.4)
        
    def test_get_eye_state_unknown(self):
        result = get_eye_state(None)
        self.assertEqual(result.state, EyeState.UNKNOWN)
        
    def test_get_eye_state_open(self):
        pts = [Point3D(0, 0, 0) for _ in range(468)]
        # Sobrescribir los puntos relevantes para hacer un EAR de 0.4 > 0.20
        # Izquierdo
        pts[33] = Point3D(0, 0, 0)
        pts[133] = Point3D(10, 0, 0)
        pts[159] = Point3D(2, 2, 0)
        pts[145] = Point3D(2, -2, 0)
        pts[158] = Point3D(8, 2, 0)
        pts[144] = Point3D(8, -2, 0)
        
        # Derecho
        pts[362] = Point3D(0, 0, 0)
        pts[263] = Point3D(10, 0, 0)
        pts[385] = Point3D(2, 2, 0)
        pts[380] = Point3D(2, -2, 0)
        pts[386] = Point3D(8, 2, 0)
        pts[374] = Point3D(8, -2, 0)
        
        landmarks = FaceLandmarksResult([], [], [], [], pts)
        res = get_eye_state(landmarks)
        self.assertEqual(res.state, EyeState.OPEN)

    def test_blink_detection(self):
        detector = BlinkDetector()
        
        # Iniciar abierto
        detector.process_state(EyeState.OPEN, 0.0)
        
        # Cerrar en t=1.0
        detector.process_state(EyeState.CLOSED, 1.0)
        # Sigue cerrado, no cuenta como parpadeo aún
        detector.process_state(EyeState.CLOSED, 1.05)
        
        metrics = detector.get_metrics(1.05)
        self.assertEqual(metrics.total_blinks, 0)
        
        # Abrir en t=1.1 (Duración 0.1s >= 0.05 min config)
        detector.process_state(EyeState.OPEN, 1.1)
        
        metrics = detector.get_metrics(1.1)
        self.assertEqual(metrics.total_blinks, 1)
        self.assertAlmostEqual(metrics.last_blink_duration, 0.1)
        self.assertAlmostEqual(metrics.avg_blink_duration, 0.1)
        
    def test_blink_too_short(self):
        detector = BlinkDetector()
        detector.process_state(EyeState.OPEN, 0.0)
        detector.process_state(EyeState.CLOSED, 1.0)
        # Abrir demasiado rápido (0.01s)
        detector.process_state(EyeState.OPEN, 1.01)
        
        metrics = detector.get_metrics(1.01)
        self.assertEqual(metrics.total_blinks, 0)

if __name__ == '__main__':
    unittest.main()
