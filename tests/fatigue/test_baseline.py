import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))

from fatigue.service import BaselineService
from fatigue.baseline import BaselineState, MetricBaseline, UserBaseline, WelfordAccumulator
from fatigue.baseline_calibrator import BaselineCalibrator, BaselineCalibratorConfig
from fatigue.models import EyeState, MouthState
from fatigue.repository import SQLiteBaselineRepository
from database.connection import DatabaseManager


class TestWelfordAccumulator(unittest.TestCase):
    def test_incremental_mean_and_sample_standard_deviation(self):
        accumulator = WelfordAccumulator()
        for value in (2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0):
            self.assertTrue(accumulator.add(value))

        self.assertEqual(accumulator.n, 8)
        self.assertAlmostEqual(accumulator.mean, 5.0)
        self.assertAlmostEqual(accumulator.std, math.sqrt(32.0 / 7.0))

    def test_rejects_non_finite_values(self):
        accumulator = WelfordAccumulator()
        for value in (float("nan"), float("inf"), float("-inf"), True):
            self.assertFalse(accumulator.add(value))
        self.assertEqual(accumulator.n, 0)
        self.assertIsNone(accumulator.mean)
        self.assertIsNone(accumulator.std)


class TestBaselineCalibrator(unittest.TestCase):
    def setUp(self):
        config = BaselineCalibratorConfig(
            frame_samples=2, blink_samples=2, rate_samples=2, perclos_samples=2
        )
        self.calibrator = BaselineCalibrator(user_id=7, config=config)

    def _add_complete_round(self, offset=0.0):
        self.calibrator.add_ear_sample(0.30 + offset, EyeState.OPEN)
        self.calibrator.add_mar_sample(0.20 + offset, MouthState.CLOSED)
        self.calibrator.add_head_pose_sample(1.0 + offset, 2.0 + offset, 3.0 + offset)
        self.calibrator.add_blink_duration(0.10 + offset)
        self.calibrator.add_blink_rate(15.0 + offset)
        self.calibrator.add_perclos_sample(0.05 + offset)

    def test_transition_calibrating_to_ready_requires_every_metric(self):
        self.assertEqual(self.calibrator.state, BaselineState.INSUFFICIENT_DATA)
        self._add_complete_round()
        self.assertEqual(self.calibrator.state, BaselineState.CALIBRATING)
        self._add_complete_round(0.01)
        self.assertEqual(self.calibrator.state, BaselineState.READY)
        self.assertEqual(self.calibrator.progress, 1.0)

    def test_invalid_and_unknown_samples_are_rejected(self):
        self.calibrator.add_ear_sample(float("nan"), EyeState.OPEN)
        self.calibrator.add_ear_sample(0.3, EyeState.UNKNOWN)
        self.calibrator.add_mar_sample(None, MouthState.CLOSED)
        self.calibrator.add_head_pose_sample(0.0, float("inf"), 0.0)
        self.calibrator.add_blink_duration(float("nan"))
        self.calibrator.add_blink_rate(0.0)
        self.calibrator.add_perclos_sample(float("nan"))

        baseline = self.calibrator.build_baseline()
        self.assertEqual(baseline.state, BaselineState.INSUFFICIENT_DATA)
        for name in ("ear", "mar", "pitch", "yaw", "roll", "blink_duration", "blink_rate", "perclos"):
            self.assertIsNone(getattr(baseline, name))

    def test_insufficient_metric_returns_none(self):
        baseline = self.calibrator.build_baseline()
        self.assertIsNone(baseline.ear)


class TestMetricDeviation(unittest.TestCase):
    def test_deviation_values(self):
        metric = MetricBaseline(mean=10.0, std=2.0, n_samples=10)
        deviation = metric.deviation(14.0)
        self.assertEqual(deviation["absolute"], 4.0)
        self.assertEqual(deviation["percent"], 40.0)
        self.assertEqual(deviation["z_score"], 2.0)

    def test_deviation_unavailable_without_data_or_variability(self):
        self.assertIsNone(MetricBaseline(None, None, 0).deviation(3.0))
        deviation = MetricBaseline(3.0, None, 1).deviation(4.0)
        self.assertIsNone(deviation["z_score"])
        self.assertIsNone(MetricBaseline(3.0, 1.0, 2).deviation(float("nan")))


class TestBaselinePersistence(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = DatabaseManager(self.path)
        self.db.initialize_database()
        self.repo = SQLiteBaselineRepository(self.db)

    def tearDown(self):
        os.remove(self.path)

    def test_save_and_load_all_metrics(self):
        metric = MetricBaseline(mean=1.5, std=0.25, n_samples=12)
        baseline = UserBaseline(
            user_id=42, state=BaselineState.CALIBRATING,
            ear=metric, blink_rate=metric, blink_duration=metric, perclos=metric,
            mar=metric, pitch=metric, yaw=metric, roll=metric,
        )
        self.repo.save(baseline)

        loaded = self.repo.get_by_user_id(42)
        self.assertEqual(loaded.state, BaselineState.CALIBRATING)
        for name in ("ear", "blink_rate", "blink_duration", "perclos", "mar", "pitch", "yaw", "roll"):
            value = getattr(loaded, name)
            self.assertEqual(value.mean, 1.5)
            self.assertEqual(value.std, 0.25)
            self.assertEqual(value.n_samples, 12)

    def test_service_loads_incomplete_calibration(self):
        self.repo.save(UserBaseline(
            user_id=5, state=BaselineState.CALIBRATING,
            ear=MetricBaseline(0.31, 0.02, 20),
        ))
        service = BaselineService(self.repo)
        service.start_for_user(5)
        self.assertEqual(service.get_baseline().ear.n_samples, 20)
        self.assertEqual(service.get_state(), BaselineState.CALIBRATING)

    def test_service_does_not_replace_stable_baseline(self):
        frame_metric = MetricBaseline(0.30, 0.01, 300)
        event_metric = MetricBaseline(12.0, 1.0, 30)
        self.repo.save(UserBaseline(
            user_id=9, state=BaselineState.READY,
            ear=frame_metric, mar=frame_metric, pitch=frame_metric,
            yaw=frame_metric, roll=frame_metric,
            blink_duration=MetricBaseline(0.12, 0.01, 3),
            blink_rate=event_metric,
            perclos=event_metric,
        ))
        service = BaselineService(self.repo)
        service.start_for_user(9)
        service.add_sample(
            ear=0.90, eye_state=EyeState.OPEN,
            mar=0.90, mouth_state=MouthState.CLOSED,
            pitch=80.0, yaw=80.0, roll=80.0,
            blink_duration=0.9, blink_bpm=50.0, perclos=0.9,
        )
        service.finish()

        loaded = self.repo.get_by_user_id(9)
        self.assertEqual(loaded.state, BaselineState.READY)
        self.assertEqual(loaded.ear.mean, 0.30)
        self.assertEqual(loaded.ear.n_samples, 300)


if __name__ == "__main__":
    unittest.main()
