import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))

from fatigue.baseline import BaselineState, MetricBaseline, UserBaseline
from fatigue.fatigue_engine import FatigueEngine, FatigueEngineConfig
from fatigue.models import FatigueLevel, FatigueMetrics


def normal_metrics(**overrides):
    values = dict(
        perclos=0.05,
        prolonged_closures=0,
        average_blink_duration=0.12,
        blink_rate=15.0,
        yawns_per_hour=0.0,
        average_yawn_duration=0.0,
        current_pitch_degrees=0.0,
        pitch_deviation_degrees=0.0,
        sustained_pitch_deviation=False,
        sustained_head_drop=False,
        session_duration_seconds=600.0,
        observation_duration_seconds=180.0,
    )
    values.update(overrides)
    return FatigueMetrics(**values)


def ready_baseline(perclos=0.05):
    return UserBaseline(
        user_id=1,
        state=BaselineState.READY,
        perclos=MetricBaseline(perclos, 0.01, 30),
        blink_duration=MetricBaseline(0.12, 0.02, 10),
        blink_rate=MetricBaseline(15.0, 2.0, 10),
        pitch=MetricBaseline(0.0, 2.0, 300),
    )


class TestFatigueEngine(unittest.TestCase):
    def test_score_is_always_clamped(self):
        assessment = FatigueEngine().assess(normal_metrics(
            perclos=99.0,
            prolonged_closures=999,
            average_blink_duration=99.0,
            blink_rate=999.0,
            yawns_per_hour=999.0,
            average_yawn_duration=99.0,
            pitch_deviation_degrees=999.0,
            sustained_pitch_deviation=True,
            sustained_head_drop=True,
            session_duration_seconds=999999.0,
        ))
        self.assertGreaterEqual(assessment.score, 0.0)
        self.assertLessEqual(assessment.score, 100.0)

    def test_normal_data_produces_low_score(self):
        assessment = FatigueEngine().assess(normal_metrics())
        self.assertLess(assessment.score, 20.0)
        self.assertEqual(assessment.level, FatigueLevel.NORMAL)

    def test_elevated_ocular_signals_raise_score(self):
        normal = FatigueEngine().assess(normal_metrics())
        elevated = FatigueEngine().assess(normal_metrics(
            perclos=0.50,
            prolonged_closures=4,
            average_blink_duration=0.70,
            blink_rate=50.0,
        ))
        self.assertGreater(elevated.score, normal.score)
        self.assertIn("perclos", elevated.active_signals)
        self.assertIn("prolonged_closures", elevated.active_signals)

    def test_independent_signal_convergence_adds_score(self):
        ocular = FatigueEngine().assess(normal_metrics(
            perclos=0.50, prolonged_closures=4, average_blink_duration=0.70,
        ))
        converged = FatigueEngine().assess(normal_metrics(
            perclos=0.50, prolonged_closures=4, average_blink_duration=0.70,
            yawns_per_hour=10.0, average_yawn_duration=8.0,
            pitch_deviation_degrees=40.0,
            sustained_pitch_deviation=True, sustained_head_drop=True,
        ))
        self.assertGreater(converged.score, ocular.score)

    def test_missing_data_is_unavailable_not_active_zero(self):
        assessment = FatigueEngine().assess(FatigueMetrics(
            observation_duration_seconds=180.0
        ))
        self.assertIn("perclos", assessment.unavailable_signals)
        self.assertNotIn("perclos", assessment.active_signals)
        self.assertLessEqual(assessment.confidence, 0.25)

    def test_personal_baseline_changes_interpretation(self):
        metrics = normal_metrics(perclos=0.15)
        fallback = FatigueEngine().assess(metrics)
        personalized = FatigueEngine().assess(metrics, ready_baseline(perclos=0.05))
        self.assertGreater(personalized.score, fallback.score)
        self.assertIn("PERCLOS elevado respecto al baseline", personalized.reasons)

    def test_levels_use_configured_boundaries(self):
        engine = FatigueEngine()
        expected = {
            0: FatigueLevel.NORMAL, 19.99: FatigueLevel.NORMAL,
            20: FatigueLevel.MILD, 39.99: FatigueLevel.MILD,
            40: FatigueLevel.MODERATE, 59.99: FatigueLevel.MODERATE,
            60: FatigueLevel.HIGH, 79.99: FatigueLevel.HIGH,
            80: FatigueLevel.VERY_HIGH, 100: FatigueLevel.VERY_HIGH,
        }
        for score, level in expected.items():
            with self.subTest(score=score):
                self.assertEqual(engine.level_for_score(score), level)

    def test_ema_prevents_single_evaluation_jump(self):
        engine = FatigueEngine(FatigueEngineConfig(ema_alpha=0.25))
        engine.assess(normal_metrics(), timestamp=0.0)
        high = engine.assess(normal_metrics(
            perclos=1.0, prolonged_closures=10,
            average_blink_duration=1.0, blink_rate=60.0,
            yawns_per_hour=20.0, average_yawn_duration=10.0,
            pitch_deviation_degrees=60.0,
            sustained_pitch_deviation=True, sustained_head_drop=True,
            session_duration_seconds=20000.0,
        ), timestamp=30.0)
        self.assertGreater(high.score, 0.0)
        self.assertLess(high.score, 40.0)

    def test_reasons_match_active_signals(self):
        assessment = FatigueEngine().assess(normal_metrics(
            perclos=0.50, prolonged_closures=3,
            current_pitch_degrees=-25.0,
            sustained_pitch_deviation=True, sustained_head_drop=True,
        ), ready_baseline())
        self.assertIn("PERCLOS elevado respecto al baseline", assessment.reasons)
        self.assertTrue(any("3 cierres prolongados" in reason for reason in assessment.reasons))
        self.assertIn("Pitch sostenido por debajo de la postura habitual", assessment.reasons)

    def test_periodic_evaluation_respects_interval(self):
        engine = FatigueEngine()
        engine.reset(timestamp=100.0)
        self.assertIsNone(engine.evaluate_if_due(normal_metrics(), timestamp=120.0))
        self.assertIsNotNone(engine.evaluate_if_due(normal_metrics(), timestamp=130.0))


if __name__ == "__main__":
    unittest.main()
