import os
import sys
import unittest
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src")
)

from monitoring.face_landmarks import FaceAnalyzer
from monitoring.models import FaceLandmarksResult


class TestFaceAnalyzer(unittest.TestCase):
    def setUp(self):
        self.landmarker = MagicMock()
        self.analyzer = FaceAnalyzer(landmarker=self.landmarker)

    def test_analyze_frame_no_face(self):
        result = MagicMock()
        result.face_landmarks = []
        self.landmarker.detect_for_video.return_value = result

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.assertIsNone(self.analyzer.analyze_frame(frame))

    def test_analyze_frame_with_face(self):
        landmarks = []
        for index in range(478):
            landmark = MagicMock()
            landmark.x = index * 0.001
            landmark.y = index * 0.001
            landmark.z = index * 0.001
            landmarks.append(landmark)

        result = MagicMock()
        result.face_landmarks = [landmarks]
        self.landmarker.detect_for_video.return_value = result

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        analysis = self.analyzer.analyze_frame(frame)

        self.assertIsInstance(analysis, FaceLandmarksResult)
        self.assertEqual(len(analysis.left_eye), len(self.analyzer.LEFT_EYE_INDICES))
        self.assertEqual(len(analysis.right_eye), len(self.analyzer.RIGHT_EYE_INDICES))
        self.assertEqual(len(analysis.mouth), len(self.analyzer.MOUTH_INDICES))
        self.assertEqual(
            len(analysis.head_orientation_points),
            len(self.analyzer.HEAD_POSE_INDICES),
        )
        self.assertEqual(len(analysis.all_points), 478)
        self.assertAlmostEqual(
            analysis.left_eye[0].x,
            self.analyzer.LEFT_EYE_INDICES[0] * 0.001,
        )
        self.landmarker.detect_for_video.assert_called_once()

    def test_rejects_invalid_frame(self):
        self.assertIsNone(self.analyzer.analyze_frame(None))
        self.assertIsNone(
            self.analyzer.analyze_frame(np.zeros((10, 10), dtype=np.uint8))
        )
        self.landmarker.detect_for_video.assert_not_called()

    def test_close_releases_landmarker(self):
        self.analyzer.close()
        self.landmarker.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
