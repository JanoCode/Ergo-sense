import os
import sys
import tempfile
import unittest
from contextlib import closing

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))

from database.connection import DatabaseManager
from fatigue.history_repository import SQLiteFatigueHistoryRepository
from fatigue.history_service import FatigueHistoryService
from fatigue.models import (
    FatigueAssessment, FatigueEventType, FatigueLevel, FatigueMetrics,
    SessionFinalMetrics,
)


class TestFatigueHistoryPersistence(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = DatabaseManager(self.path)
        self.db.initialize_database()
        with closing(self.db.get_connection()) as conn:
            cursor = conn.execute("INSERT INTO users (name) VALUES ('Test')")
            self.user_id = cursor.lastrowid
            cursor = conn.execute(
                "INSERT INTO sessions (user_id, started_at) VALUES (?, ?)",
                (self.user_id, "2026-01-01T10:00:00"),
            )
            self.session_id = cursor.lastrowid
            conn.commit()
        self.repository = SQLiteFatigueHistoryRepository(self.db)
        self.service = FatigueHistoryService(self.repository)

    def tearDown(self):
        os.remove(self.path)

    def _assessment(self, timestamp=1000.0, score=45.0, level=FatigueLevel.MODERATE):
        return FatigueAssessment(
            timestamp=timestamp, score=score, level=level, confidence=0.8,
            active_signals=["perclos"], unavailable_signals=["yawn_duration"],
            reasons=["PERCLOS elevado"],
        )

    def test_assessment_persistence_and_session_relationship(self):
        stored = self.service.record_assessment(
            self.session_id, self.user_id, self._assessment(),
            FatigueMetrics(perclos=0.3, pitch_deviation_degrees=12.0),
        )
        recovered = self.service.get_assessments(self.session_id)

        self.assertIsNotNone(stored.id)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].session_id, self.session_id)
        self.assertEqual(recovered[0].user_id, self.user_id)
        self.assertEqual(recovered[0].level, FatigueLevel.MODERATE)
        self.assertEqual(recovered[0].active_signals, ["perclos"])
        self.assertAlmostEqual(recovered[0].perclos, 0.3)

    def test_relevant_events_are_persisted(self):
        self.service.record_assessment(
            self.session_id, self.user_id, self._assessment(level=FatigueLevel.HIGH),
            FatigueMetrics(
                prolonged_closures=2, yawns=1, sustained_head_drop=True,
                pitch_deviation_degrees=22.0,
            ),
        )
        events = self.service.get_events(self.session_id)
        event_types = {event.event_type for event in events}

        self.assertIn(FatigueEventType.PROLONGED_EYE_CLOSURE, event_types)
        self.assertIn(FatigueEventType.YAWN, event_types)
        self.assertIn(FatigueEventType.HEAD_DROP, event_types)
        self.assertIn(FatigueEventType.ENTERED_MODERATE, event_types)
        self.assertIn(FatigueEventType.ENTERED_HIGH, event_types)
        self.assertTrue(all(event.user_id == self.user_id for event in events))

    def test_events_from_final_partial_window_are_persisted(self):
        self.service.record_metric_events(
            self.session_id, self.user_id, 1099.0,
            FatigueMetrics(prolonged_closures=1, yawns=2, sustained_head_drop=True),
        )
        events = self.service.get_events(self.session_id)
        self.assertEqual(len(events), 3)
        self.assertEqual(
            {event.event_type for event in events},
            {
                FatigueEventType.PROLONGED_EYE_CLOSURE,
                FatigueEventType.YAWN,
                FatigueEventType.HEAD_DROP,
            },
        )

    def test_duplicate_assessment_and_events_are_ignored(self):
        assessment = self._assessment(level=FatigueLevel.HIGH)
        metrics = FatigueMetrics(prolonged_closures=1, yawns=1)
        self.service.record_assessment(self.session_id, self.user_id, assessment, metrics)
        self.service.record_assessment(self.session_id, self.user_id, assessment, metrics)

        self.assertEqual(len(self.service.get_assessments(self.session_id)), 1)
        events = self.service.get_events(self.session_id)
        self.assertEqual(
            len([event for event in events if event.event_type == FatigueEventType.YAWN]), 1
        )

    def test_summary_generation_and_historical_recovery(self):
        start = 1000.0
        self.service.record_assessment(
            self.session_id, self.user_id,
            self._assessment(start + 30, 25.0, FatigueLevel.MILD),
            FatigueMetrics(perclos=0.10, pitch_deviation_degrees=8.0),
        )
        self.service.record_assessment(
            self.session_id, self.user_id,
            self._assessment(start + 90, 65.0, FatigueLevel.HIGH),
            FatigueMetrics(perclos=0.30, pitch_deviation_degrees=25.0),
        )
        summary = self.service.finalize_session(
            self.session_id, self.user_id, start,
            SessionFinalMetrics(
                duration_seconds=600, total_blinks=120,
                average_blink_rate=12.0, average_blink_duration=0.18,
                prolonged_closures=3, yawns=2, max_head_deviation_degrees=31.0,
            ),
        )
        recovered = self.service.get_summary(self.session_id)

        self.assertEqual(summary, recovered)
        self.assertEqual(recovered.total_blinks, 120)
        self.assertAlmostEqual(recovered.average_perclos, 0.20)
        self.assertAlmostEqual(recovered.max_perclos, 0.30)
        self.assertAlmostEqual(recovered.average_score, 45.0)
        self.assertAlmostEqual(recovered.max_score, 65.0)
        self.assertEqual(recovered.max_level, FatigueLevel.HIGH)
        self.assertAlmostEqual(recovered.max_head_deviation_degrees, 31.0)
        self.assertAlmostEqual(recovered.time_to_mild_seconds, 30.0)
        self.assertAlmostEqual(recovered.time_to_moderate_seconds, 90.0)
        self.assertAlmostEqual(recovered.time_to_high_seconds, 90.0)

    def test_unreached_levels_and_missing_assessments_are_null(self):
        summary = self.service.finalize_session(
            self.session_id, self.user_id, 1000.0,
            SessionFinalMetrics(
                duration_seconds=60, total_blinks=0,
                average_blink_rate=None, average_blink_duration=None,
                prolonged_closures=0, yawns=0,
            ),
        )
        self.assertIsNone(summary.average_score)
        self.assertIsNone(summary.max_score)
        self.assertIsNone(summary.max_level)
        self.assertIsNone(summary.average_perclos)
        self.assertIsNone(summary.time_to_mild_seconds)
        self.assertIsNone(summary.time_to_moderate_seconds)
        self.assertIsNone(summary.time_to_high_seconds)


if __name__ == "__main__":
    unittest.main()
