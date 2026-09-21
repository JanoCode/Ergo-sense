import gc
import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../src"))

from database.connection import DatabaseManager
from fatigue.analytics import FatigueAnalyticsService, SQLiteFatigueAnalyticsRepository
from fatigue.fatigue_engine import FatigueEngine
from fatigue.history_repository import SQLiteFatigueHistoryRepository
from fatigue.history_service import FatigueHistoryService
from fatigue.models import AnalyticsPeriod, FatigueMetrics, SessionFinalMetrics
from sessions.repository import SQLiteSessionRepository
from sessions.service import SessionService
from users.repository import SQLiteUserRepository
from users.service import UserService


class TestEndToEndFatigueFlow(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = DatabaseManager(self.path)
        self.db.initialize_database()

    def tearDown(self):
        gc.collect()
        os.remove(self.path)

    def test_user_session_assessment_history_and_analytics(self):
        user_service = UserService(SQLiteUserRepository(self.db))
        session_service = SessionService(
            SQLiteSessionRepository(self.db), user_service
        )
        history_service = FatigueHistoryService(
            SQLiteFatigueHistoryRepository(self.db)
        )
        analytics_service = FatigueAnalyticsService(
            SQLiteFatigueAnalyticsRepository(self.db)
        )

        user = user_service.create_user("Usuario integración")
        user_service.set_active_user(user)
        session = session_service.start_session()
        timestamp = session.started_at.timestamp() + 30.0

        metrics = FatigueMetrics(
            perclos=0.45, prolonged_closures=3,
            average_blink_duration=0.5, blink_rate=30.0,
            yawns_per_hour=6.0, yawns=1, average_yawn_duration=4.0,
            pitch_deviation_degrees=25.0,
            sustained_pitch_deviation=True, sustained_head_drop=True,
            session_duration_seconds=1800.0,
            observation_duration_seconds=1800.0,
        )
        assessment = FatigueEngine().assess(metrics, timestamp=timestamp)
        history_service.record_assessment(
            session.id, user.id, assessment, metrics
        )

        ended = session_service.end_session()
        history_service.finalize_session(
            ended.id, user.id, session.started_at.timestamp(),
            SessionFinalMetrics(
                duration_seconds=3600, total_blinks=90,
                average_blink_rate=1.5, average_blink_duration=0.2,
                prolonged_closures=3, yawns=1,
                max_head_deviation_degrees=25.0,
            ),
        )

        sessions = session_service.get_user_sessions(user.id)
        assessments = history_service.get_assessments(session.id)
        summary = history_service.get_summary(session.id)
        analytics = analytics_service.analyze(
            user.id, AnalyticsPeriod.LAST_7_DAYS, datetime.now()
        )

        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(assessments), 1)
        self.assertEqual(assessments[0].session_id, session.id)
        self.assertEqual(summary.total_blinks, 90)
        self.assertEqual(analytics.current_period.session_count, 1)
        self.assertEqual(analytics.current_period.comparable_session_count, 1)
        self.assertEqual(len(analytics.daily), 1)


if __name__ == "__main__":
    unittest.main()
