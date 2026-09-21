import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src")
)

from fatigue.blink_detector import BlinkDetector
from fatigue.head_pose import HeadPoseEstimator
from fatigue.perclos import PerclosCalculator, ProlongedClosureDetector
from fatigue.yawn_detector import YawnDetector
from monitoring.monitoring_worker import MonitoringWorker


class TestMonitoringWorker(unittest.TestCase):
    def test_overlay_is_optional_and_analysis_still_runs(self):
        from monitoring.models import FaceLandmarksResult, Point3D
        analyzer = MagicMock()
        analyzer.analyze_frame.return_value = FaceLandmarksResult(
            [], [], [], [], [Point3D(0, 0, 0) for _ in range(478)]
        )
        worker = self._worker(MagicMock(), lambda: analyzer)
        worker.head_pose_estimator = MagicMock()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        sample = worker._analyze(frame, 1, analyzer)
        self.assertIs(sample.frame_rgb, frame)
        analyzer.draw_landmarks.assert_not_called()
        worker.show_landmarks.set()
        worker._analyze(frame, 2, analyzer)
        analyzer.draw_landmarks.assert_called_once()
        self.assertEqual(analyzer.analyze_frame.call_count, 2)

    def _worker(self, camera, analyzer_factory):
        return MonitoringWorker(
            camera_service=camera,
            face_analyzer_factory=analyzer_factory,
            blink_detector=BlinkDetector(),
            perclos_calculator=PerclosCalculator(),
            prolonged_detector=ProlongedClosureDetector(),
            yawn_detector=YawnDetector(),
            head_pose_estimator=HeadPoseEstimator(),
            analysis_fps=30,
            display_fps=30,
        )

    def test_worker_opens_camera_processes_frame_and_releases_resources(self):
        camera = MagicMock()
        camera.start.return_value = True
        camera.properties.return_value = (1, 640, 480, 30.0)
        analyzer = MagicMock()
        analyzer.analyze_frame.side_effect = lambda _: (
            worker.request_stop() or None
        )
        factory = MagicMock(return_value=analyzer)
        worker = self._worker(camera, factory)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        camera.get_frame.return_value = frame
        samples = []
        worker.sample_ready.connect(samples.append)

        worker.run()

        factory.assert_called_once_with()
        analyzer.analyze_frame.assert_called_once()
        analyzer.close.assert_called_once()
        camera.stop.assert_called_once()
        self.assertGreaterEqual(len(samples), 1)
        self.assertTrue(any(sample.analyzed for sample in samples))

    def test_first_frame_is_emitted_while_analyzer_is_still_initializing(self):
        camera = MagicMock()
        camera.start.return_value = True
        camera.properties.return_value = (0, 640, 480, 30.0)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        analyzer = MagicMock()
        initialized = threading.Event()

        def slow_factory():
            time.sleep(0.2)
            initialized.set()
            return analyzer

        worker = self._worker(camera, slow_factory)
        reads = 0

        def read_frame():
            nonlocal reads
            reads += 1
            if reads >= 2:
                worker.request_stop()
            return frame

        camera.get_frame.side_effect = read_frame
        samples_before_initialization = []
        worker.sample_ready.connect(
            lambda sample: samples_before_initialization.append(
                (sample, initialized.is_set())
            )
        )

        worker.run()

        self.assertGreaterEqual(len(samples_before_initialization), 1)
        first_sample, analyzer_was_ready = samples_before_initialization[0]
        self.assertFalse(analyzer_was_ready)
        self.assertFalse(first_sample.analyzed)
        analyzer.close.assert_called_once()

    def test_worker_does_not_initialize_model_without_camera(self):
        camera = MagicMock()
        camera.start.return_value = False
        factory = MagicMock()
        worker = self._worker(camera, factory)
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        factory.assert_not_called()
        camera.stop.assert_called_once()
        self.assertEqual(len(errors), 1)
        self.assertIn("índices 0, 1 o 2", errors[0])


if __name__ == "__main__":
    unittest.main()
