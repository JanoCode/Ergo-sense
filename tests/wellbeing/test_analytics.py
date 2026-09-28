from datetime import datetime, timedelta

from sessions.models import Session
from wellbeing.analytics import WellbeingAnalyticsService
from wellbeing.models import (
    BreakCompletionType,
    BreakEvent,
    BreakEventType,
    WellbeingBreak,
)


NOW = datetime(2026, 9, 28, 12, 0, 0)


class SessionSource:
    def __init__(self, sessions):
        self.sessions = sessions

    def get_user_sessions(self, user_id):
        return [item for item in self.sessions if item.user_id == user_id]


class BreakSource:
    def __init__(self, breaks=None, events=None):
        self.breaks = breaks or {}
        self.events = events or {}

    def get_breaks_by_session(self, session_id):
        return self.breaks.get(session_id, [])

    def get_by_session(self, session_id):
        return self.events.get(session_id, [])


def completed_break(session_id, started_at, seconds=600):
    return WellbeingBreak(
        id=session_id,
        session_id=session_id,
        user_id=1,
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=seconds),
        duration_seconds=seconds,
        completion_type=BreakCompletionType.AUTOMATIC,
    )


def build_service():
    current = Session(
        id=1,
        user_id=1,
        started_at=NOW - timedelta(hours=2),
        ended_at=NOW,
        duration_seconds=7200,
    )
    previous_week = Session(
        id=2,
        user_id=1,
        started_at=NOW - timedelta(days=10),
        ended_at=NOW - timedelta(days=10) + timedelta(hours=1),
        duration_seconds=3600,
    )
    old = Session(
        id=3,
        user_id=1,
        started_at=NOW - timedelta(days=20),
        ended_at=NOW - timedelta(days=20) + timedelta(minutes=30),
        duration_seconds=1800,
    )
    first_break = completed_break(1, current.started_at + timedelta(hours=1))
    second_break = completed_break(
        11, current.started_at + timedelta(hours=1, minutes=30), 300
    )
    previous_break = completed_break(
        2, previous_week.started_at + timedelta(minutes=30), 300
    )
    postponed = BreakEvent(
        session_id=1,
        user_id=1,
        event_type=BreakEventType.BREAK_POSTPONED,
        timestamp=current.started_at + timedelta(minutes=50),
    )
    repo = BreakSource(
        breaks={1: [first_break, second_break], 2: [previous_break]},
        events={1: [postponed]},
    )
    service = WellbeingAnalyticsService(
        SessionSource([current, previous_week, old]), repo, lambda: NOW
    )
    return service, current, previous_week, old


def test_session_summary_calculates_usage_and_breaks():
    service, session, _, _ = build_service()
    summary = service.session_summary(session)
    assert summary.total_duration_seconds == 7200
    assert summary.break_seconds == 900
    assert summary.work_seconds == 6300
    assert summary.completed_breaks == 2
    assert summary.postponed_breaks == 1
    assert summary.average_break_seconds == 450
    assert summary.has_break_data is True


def test_session_summary_calculates_max_continuous_usage():
    service, session, _, _ = build_service()
    summary = service.session_summary(session)
    assert summary.continuous_before_break_seconds == (3600, 1200)
    assert summary.max_continuous_usage_seconds == 3600


def test_seven_day_statistics():
    service, _, _, _ = build_service()
    stats = service.period_stats(1, 7)
    assert stats.session_count == 1
    assert stats.total_usage_seconds == 6300
    assert stats.total_break_seconds == 900
    assert stats.completed_breaks == 2
    assert stats.average_breaks_per_session == 2
    assert stats.average_continuous_before_break_seconds == 2400
    assert stats.total_postponed_breaks == 1


def test_thirty_day_statistics_include_all_sessions():
    service, _, _, _ = build_service()
    stats = service.period_stats(1, 30)
    assert stats.session_count == 3
    assert stats.total_usage_seconds == 11400
    assert stats.total_break_seconds == 1200
    assert stats.completed_breaks == 3


def test_old_session_without_break_data_is_explicit():
    service, _, _, old = build_service()
    summary = service.session_summary(old)
    assert summary.has_break_data is False
    assert summary.completed_breaks == 0
    assert summary.break_seconds == 0
    assert summary.max_continuous_usage_seconds == 1800


def test_empty_period_returns_zero_values():
    service, _, _, _ = build_service()
    stats = service.period_stats(99, 7)
    assert stats.session_count == 0
    assert stats.total_usage_seconds == 0
    assert stats.average_breaks_per_session == 0
    assert stats.average_continuous_before_break_seconds == 0


def test_weekly_comparison_is_descriptive():
    service, _, _, _ = build_service()
    assert service.compare_weekly_breaks(1) == (
        "Esta semana realizaste 2 pausas frente a 1 la semana anterior."
    )


def test_comparison_without_data_has_empty_state():
    service, _, _, _ = build_service()
    assert service.compare_weekly_breaks(99) == (
        "Aún no hay datos para comparar estas semanas."
    )
