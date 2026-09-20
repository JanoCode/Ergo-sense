import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from infrastructure.face_analyzer import FaceAnalyzer
from domain.facial_landmarks import FaceLandmarksResult

class TestFaceAnalyzer(unittest.TestCase):
    @patch('mediapipe.solutions.face_mesh.FaceMesh')
    def setUp(self, mock_facemesh):
        self.mock_facemesh_instance = MagicMock()
        mock_facemesh.return_value = self.mock_facemesh_instance
        self.analyzer = FaceAnalyzer()

    def test_analyze_frame_no_face(self):
        # Configurar mock para devolver sin caras
        mock_results = MagicMock()
        mock_results.multi_face_landmarks = None
        self.analyzer.face_mesh.process.return_value = mock_results
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = self.analyzer.analyze_frame(frame)
        
        self.assertIsNone(result)
        
    def test_analyze_frame_with_face(self):
        # Crear landmarks falsos (468 puntos)
        mock_results = MagicMock()
        mock_landmarks = MagicMock()
        
        fake_landmarks = []
        for i in range(468):
            lm = MagicMock()
            lm.x = i * 0.001
            lm.y = i * 0.001
            lm.z = i * 0.001
            fake_landmarks.append(lm)
            
        mock_landmarks.landmark = fake_landmarks
        mock_results.multi_face_landmarks = [mock_landmarks]
        self.analyzer.face_mesh.process.return_value = mock_results
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = self.analyzer.analyze_frame(frame)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, FaceLandmarksResult)
        
        # Validar extracciones de puntos
        self.assertEqual(len(result.left_eye), len(self.analyzer.LEFT_EYE_INDICES))
        self.assertEqual(len(result.right_eye), len(self.analyzer.RIGHT_EYE_INDICES))
        self.assertEqual(len(result.mouth), len(self.analyzer.MOUTH_INDICES))
        self.assertEqual(len(result.head_orientation_points), len(self.analyzer.HEAD_POSE_INDICES))
        self.assertEqual(len(result.all_points), 468)
        
        # Verificar que el mapeo es correcto (usando x como índice)
        first_left_eye_idx = self.analyzer.LEFT_EYE_INDICES[0]
        self.assertAlmostEqual(result.left_eye[0].x, first_left_eye_idx * 0.001)

if __name__ == '__main__':
    unittest.main()
