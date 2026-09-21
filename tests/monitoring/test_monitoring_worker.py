import os
import sys
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
        analyzer.analyze_frame.return_value = None
        factory = MagicMock(return_value=analyzer)
        worker = self._worker(camera, factory)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        def one_frame():
            worker.request_stop()
            return frame

        camera.get_frame.side_effect = one_frame
        samples = []
        worker.sample_ready.connect(samples.append)

        worker.run()

        factory.assert_called_once_with()
        analyzer.analyze_frame.assert_called_once()
        analyzer.close.assert_called_once()
        camera.stop.assert_called_once()
        self.assertEqual(len(samples), 1)
        self.assertTrue(samples[0].analyzed)
        self.assertFalse(samples[0].face_detected)

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
