import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))

from fatigue.analytics import FatigueAnalyticsService
from fatigue.models import (
    AnalyticsPeriod, FatigueLevel, FatigueTrend, HistoricalFatigueSession,
    SessionFatigueSummary,
)


def history_session(
    started_at, duration=3600, score=40.0, max_score=50.0,
    level=FatigueLevel.MODERATE, mild=1200.0, moderate=2400.0, high=None,
    perclos=0.15, closures=2, yawns=1, session_id=1,
):
    return HistoricalFatigueSession(
        started_at=started_at,
        summary=SessionFatigueSummary(
            session_id=session_id, user_id=1, duration_seconds=duration,
            total_blinks=60, average_blink_rate=12.0,
            average_blink_duration=0.15, average_perclos=perclos,
            max_perclos=perclos, prolonged_closures=closures, yawns=yawns,
            max_head_deviation_degrees=10.0, average_score=score,
            max_score=max_score, max_level=level,
            time_to_mild_seconds=mild, time_to_moderate_seconds=moderate,
            time_to_high_seconds=high,
        ),
    )


class FakeAnalyticsRepository:
    def __init__(self, records):
        self.records = records

    def get_user_history(self, user_id, start=None, end=None):
        return [
            item for item in self.records
            if (start is None or item.started_at >= start)
            and (end is None or item.started_at < end)
        ]


class TestFatigueAnalytics(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 20, 12, 0, 0)

    def _service(self, records):
        return FatigueAnalyticsService(FakeAnalyticsRepository(records))

    def test_statistics_for_7_and_30_days(self):
        records = [
            history_session(self.now - timedelta(days=2), session_id=1),
            history_session(self.now - timedelta(days=10), session_id=2),
            history_session(self.now - timedelta(days=40), session_id=3),
        ]
        service = self._service(records)
        seven = service.analyze(1, AnalyticsPeriod.LAST_7_DAYS, self.now)
        thirty = service.analyze(1, AnalyticsPeriod.LAST_30_DAYS, self.now)

        self.assertEqual(seven.current_period.session_count, 1)
        self.assertEqual(thirty.current_period.session_count, 2)
        self.assertEqual(thirty.current_period.total_monitored_seconds, 7200)
        self.assertEqual(len(thirty.daily), 2)

    def test_null_values_are_ignored_not_zero(self):
        first = history_session(self.now - timedelta(days=1), score=None, moderate=None)
        second = history_session(self.now - timedelta(days=2), score=60.0, moderate=1800.0)
        stats = self._service([]).calculate_stats([first, second])
        self.assertEqual(stats.average_score, 60.0)
        self.assertEqual(stats.average_time_to_moderate_seconds, 1800.0)

    def test_period_comparison_absolute_and_percentage(self):
        service = self._service([])
        previous = service.calculate_stats([
            history_session(self.now, score=50.0, moderate=3600.0)
        ])
        current = service.calculate_stats([
            history_session(self.now, score=40.0, moderate=3000.0)
        ])
        changes = service.compare_periods(current, previous)
        self.assertEqual(changes["average_score"].absolute, -10.0)
        self.assertEqual(changes["average_score"].percentage, -20.0)
        self.assertEqual(
            changes["average_time_to_moderate_seconds"].absolute, -600.0
        )

    def test_level_percentages_use_only_available_levels(self):
        records = [
            history_session(self.now, level=FatigueLevel.HIGH),
            history_session(self.now, level=FatigueLevel.MODERATE),
            history_session(self.now, level=FatigueLevel.NORMAL, moderate=None),
            history_session(self.now, level=None, moderate=None),
        ]
        stats = self._service([]).calculate_stats(records)
        self.assertAlmostEqual(stats.moderate_session_percentage, 200 / 3)
        self.assertAlmostEqual(stats.high_session_percentage, 100 / 3)

    def test_short_session_does_not_count_as_improvement(self):
        short = history_session(
            self.now, duration=300, score=0.0, max_score=0.0,
            level=FatigueLevel.NORMAL, mild=None, moderate=None,
        )
        normal = history_session(self.now, duration=3600, score=55.0)
        stats = self._service([]).calculate_stats([short, normal])
        self.assertEqual(stats.session_count, 2)
        self.assertEqual(stats.comparable_session_count, 1)
        self.assertEqual(stats.average_score, 55.0)

    def _trend(self, previous_kwargs, current_kwargs):
        previous = [
            history_session(self.now - timedelta(days=10 + index), **previous_kwargs)
            for index in range(3)
        ]
        current = [
            history_session(self.now - timedelta(days=1 + index), **current_kwargs)
            for index in range(3)
        ]
        result = self._service(previous + current).analyze(
            1, AnalyticsPeriod.LAST_7_DAYS, self.now
        )
        return result

    def test_improving_trend(self):
        result = self._trend(
            dict(score=60.0, moderate=2400.0, level=FatigueLevel.HIGH, high=3000.0),
            dict(score=45.0, moderate=3300.0, level=FatigueLevel.MODERATE, high=None),
        )
        self.assertEqual(result.trend, FatigueTrend.IMPROVING)

    def test_stable_trend(self):
        result = self._trend(
            dict(score=50.0, moderate=3000.0, level=FatigueLevel.MODERATE),
            dict(score=52.0, moderate=3100.0, level=FatigueLevel.MODERATE),
        )
        self.assertEqual(result.trend, FatigueTrend.STABLE)

    def test_worsening_trend(self):
        result = self._trend(
            dict(score=40.0, moderate=3600.0, level=FatigueLevel.MODERATE),
            dict(score=60.0, moderate=2400.0, level=FatigueLevel.HIGH, high=3000.0),
        )
        self.assertEqual(result.trend, FatigueTrend.WORSENING)

    def test_insufficient_data_trend_and_insight(self):
        records = [history_session(self.now - timedelta(days=1))]
        result = self._service(records).analyze(
            1, AnalyticsPeriod.LAST_7_DAYS, self.now
        )
        self.assertEqual(result.trend, FatigueTrend.INSUFFICIENT_DATA)
        self.assertIn("No existen suficientes sesiones comparables", result.insights[0])

    def test_insight_describes_moderate_time_change(self):
        result = self._trend(
            dict(score=50.0, moderate=3600.0, level=FatigueLevel.MODERATE),
            dict(score=60.0, moderate=2160.0, level=FatigueLevel.HIGH, high=3000.0),
        )
        self.assertTrue(any(
            "disminuyó 24 minutos" in insight for insight in result.insights
        ))


if __name__ == "__main__":
    unittest.main()
