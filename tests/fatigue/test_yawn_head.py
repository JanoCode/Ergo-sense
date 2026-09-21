import unittest
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

from monitoring.models import FaceLandmarksResult, Point3D
from fatigue.models import MouthState, HeadPoseAngles
from fatigue.mouth_metrics import calculate_mar_from_points, get_mouth_state, MARConfig
from fatigue.yawn_detector import YawnDetector, YawnConfig
from fatigue.head_pose import HeadPoseEstimator, HeadPoseConfig


class TestMARCalculator(unittest.TestCase):
    def test_mar_is_independent_of_image_aspect_ratio(self):
        for width, height in ((640, 480), (1280, 720), (480, 640)):
            pts = [Point3D(0, 0, 0) for _ in range(478)]
            for index, x, y in ((61, 100, 200), (291, 200, 200),
                                (82, 130, 170), (87, 130, 230),
                                (13, 150, 170), (14, 150, 230)):
                pts[index] = Point3D(x / width, y / height, 0)
            mar, state = get_mouth_state(
                FaceLandmarksResult([], [], [], [], pts),
                frame_width=width, frame_height=height,
            )
            self.assertAlmostEqual(mar, 0.6)
            self.assertEqual(state, MouthState.OPEN)

    def test_personal_mar_cannot_lower_general_threshold(self):
        from fatigue.baseline import MetricBaseline
        pts = [Point3D(0, 0, 0) for _ in range(478)]
        pts[291] = Point3D(1, 0, 0)
        pts[87] = pts[14] = Point3D(0, 0.6, 0)
        landmarks = FaceLandmarksResult([], [], [], [], pts)
        self.assertEqual(get_mouth_state(landmarks)[1], MouthState.OPEN)
        self.assertEqual(get_mouth_state(
            landmarks, baseline=MetricBaseline(0.45, 0.1, 100)
        )[1], MouthState.CLOSED)

    def test_calculate_mar_open(self):
        # Boca muy abierta: distancia vertical grande
        # horiz = 10, vert1 = 5, vert2 = 5 → MAR = 10/(2*10) = 0.5
        mar = calculate_mar_from_points(
            Point3D(0, 0, 0), Point3D(10, 0, 0),   # izq, der
            Point3D(2, 2, 0), Point3D(2, -3, 0),    # top1, bot1
            Point3D(8, 2, 0), Point3D(8, -3, 0),    # top2, bot2
        )
        self.assertAlmostEqual(mar, 0.5)

    def test_calculate_mar_zero_horizontal(self):
        mar = calculate_mar_from_points(
            Point3D(0, 0, 0), Point3D(0, 0, 0),
            Point3D(0, 1, 0), Point3D(0, -1, 0),
            Point3D(0, 1, 0), Point3D(0, -1, 0),
        )
        self.assertIsNone(mar)

    def test_mouth_state_unknown_no_landmarks(self):
        _, state = get_mouth_state(None)
        self.assertEqual(state, MouthState.UNKNOWN)

    def test_mouth_state_unknown_insufficient(self):
        # Less than 468 points
        pts = [Point3D(0, 0, 0) for _ in range(100)]
        lm = FaceLandmarksResult([], [], [], [], pts)
        _, state = get_mouth_state(lm)
        self.assertEqual(state, MouthState.UNKNOWN)

    def test_mouth_state_closed(self):
        # MAR muy bajo → CLOSED
        pts = [Point3D(float(i) * 0.001, 0, 0) for i in range(468)]
        # Esquinas lejanas, boca casi cerrada
        pts[61]  = Point3D(0.0, 0.0, 0)
        pts[291] = Point3D(0.1, 0.0, 0)   # horiz = 0.1
        pts[82]  = Point3D(0.02, 0.001, 0)
        pts[87]  = Point3D(0.02, -0.001, 0)  # vert1 = 0.002
        pts[13]  = Point3D(0.08, 0.001, 0)
        pts[14]  = Point3D(0.08, -0.001, 0)  # vert2 = 0.002
        # MAR = (0.002+0.002)/(2*0.1) = 0.02 < 0.5
        lm = FaceLandmarksResult([], [], [], [], pts)
        mar, state = get_mouth_state(lm)
        self.assertEqual(state, MouthState.CLOSED)


class TestYawnDetector(unittest.TestCase):
    def test_unknown_breaks_continuity(self):
        self.det.process_state(MouthState.OPEN, 1)
        self.det.process_state(MouthState.UNKNOWN, 2)
        self.det.process_state(MouthState.CLOSED, 5)
        self.assertEqual(self.det.total_yawns, 0)

    def test_reopen_counts_new_event(self):
        for timestamp in (0, 5):
            self.det.process_state(MouthState.OPEN, timestamp)
            self.det.process_state(MouthState.OPEN, timestamp + 2)
            self.det.process_state(MouthState.CLOSED, timestamp + 3)
        self.assertEqual(self.det.total_yawns, 2)

    def test_speech_like_short_openings_do_not_accumulate(self):
        for timestamp in range(20):
            self.det.process_state(MouthState.OPEN, timestamp)
            self.det.process_state(MouthState.CLOSED, timestamp + 0.4)
        self.assertEqual(self.det.total_yawns, 0)

    def setUp(self):
        config = YawnConfig()
        config.MIN_OPEN_SECONDS = 2.0
        self.det = YawnDetector(config)
        self.det.reset(0.0)

    def test_short_open_not_yawn(self):
        self.det.process_state(MouthState.CLOSED, 0.0)
        self.det.process_state(MouthState.OPEN, 1.0)
        self.det.process_state(MouthState.CLOSED, 1.5)  # 0.5s < 2.0s
        metrics = self.det.get_metrics(1.5)
        self.assertEqual(metrics.total_yawns, 0)

    def test_valid_yawn_detected(self):
        self.det.process_state(MouthState.CLOSED, 0.0)
        self.det.process_state(MouthState.OPEN, 1.0)
        self.det.process_state(MouthState.CLOSED, 4.0)  # 3.0s >= 2.0s
        metrics = self.det.get_metrics(4.0)
        self.assertEqual(metrics.total_yawns, 1)
        self.assertAlmostEqual(metrics.last_duration, 3.0)

    def test_no_double_count_while_open(self):
        self.det.process_state(MouthState.CLOSED, 0.0)
        self.det.process_state(MouthState.OPEN, 1.0)
        self.det.process_state(MouthState.OPEN, 3.5)  # supera umbral → cuenta 1
        self.det.process_state(MouthState.OPEN, 5.0)  # sigue abierto → NO cuenta de nuevo
        metrics = self.det.get_metrics(5.0)
        self.assertEqual(metrics.total_yawns, 1)

    def test_unknown_ignored(self):
        self.det.process_state(MouthState.CLOSED, 0.0)
        self.det.process_state(MouthState.OPEN, 1.0)
        self.det.process_state(MouthState.UNKNOWN, 2.0)  # no interrumpe ni cuenta
        metrics = self.det.get_metrics(2.0)
        self.assertEqual(metrics.total_yawns, 0)


class TestHeadPoseEstimator(unittest.TestCase):
    def setUp(self):
        config = HeadPoseConfig()
        config.SUSTAINED_SECONDS = 2.0
        config.DOWN_PITCH_THRESHOLD = 10.0
        config.DEVIATION_THRESHOLD = 15.0
        self.estimator = HeadPoseEstimator(config)

    def test_no_landmarks_returns_no_angles(self):
        result = self.estimator.process(None, 640, 480, 0.0)
        self.assertIsNone(result.angles)
        self.assertFalse(result.has_reference)

    def test_deviation_calculation(self):
        ref = HeadPoseAngles(pitch=5.0, yaw=2.0, roll=1.0)
        current = HeadPoseAngles(pitch=20.0, yaw=5.0, roll=3.0)
        dev = HeadPoseAngles(
            pitch=current.pitch - ref.pitch,
            yaw=current.yaw - ref.yaw,
            roll=current.roll - ref.roll,
        )
        self.assertAlmostEqual(dev.pitch, 15.0)
        self.assertAlmostEqual(dev.yaw, 3.0)
        self.assertAlmostEqual(dev.roll, 2.0)

    def test_total_deviation_magnitude(self):
        dev = HeadPoseAngles(pitch=3.0, yaw=4.0, roll=0.0)
        magnitude = math.sqrt(dev.pitch**2 + dev.yaw**2 + dev.roll**2)
        self.assertAlmostEqual(magnitude, 5.0)


if __name__ == '__main__':
    unittest.main()
