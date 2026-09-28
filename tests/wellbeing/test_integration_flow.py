from datetime import datetime, timedelta

from database.connection import DatabaseManager
from sessions.repository import SQLiteSessionRepository
from sessions.service import SessionService
from users.repository import SQLiteUserRepository
from users.service import UserService
from wellbeing.analytics import WellbeingAnalyticsService
from wellbeing.models import BreakCompletionType, BreakEventType, CycleState
from wellbeing.repository import SQLiteBreakEventRepository
from wellbeing.service import WellbeingService


class ControlledClock:
    def __init__(self, current):
        self.current = current

    def __call__(self):
        return self.current

    def advance(self, **kwargs):
        self.current += timedelta(**kwargs)


def build_stack(tmp_path, started_at):
    database = DatabaseManager(str(tmp_path / "wellbeing-flow.db"))
    database.initialize_database()
    users = UserService(SQLiteUserRepository(database))
    sessions = SessionService(
        SQLiteSessionRepository(database), users, started_at
    )
    breaks = SQLiteBreakEventRepository(database)
    wellbeing = WellbeingService(sessions, breaks, started_at)
    analytics = WellbeingAnalyticsService(sessions, breaks, started_at)
    return users, sessions, breaks, wellbeing, analytics


def test_complete_wellbeing_flow_is_persisted_and_isolated_by_user(tmp_path):
    clock = ControlledClock(datetime(2026, 9, 28, 9, 0, 0))
    users, sessions, breaks, wellbeing, analytics = build_stack(tmp_path, clock)
    user = users.create_user("Ada")
    other_user = users.create_user("Grace")
    users.set_active_user(user)

    session = sessions.start_session()
    clock.advance(minutes=50)
    assert wellbeing.get_cycle_state() == CycleState.BREAK_DUE
    assert wellbeing.should_show_reminder() is True
    wellbeing.postpone()
    assert wellbeing.get_state().continuous_usage_seconds == 3000

    clock.advance(minutes=10)
    assert wellbeing.should_show_reminder() is True
    wellbeing.start_break()
    assert wellbeing.get_cycle_state() == CycleState.BREAKING
    assert wellbeing.get_break_remaining_seconds() == 300

    clock.advance(minutes=5)
    assert wellbeing.get_cycle_state() == CycleState.WORKING
    assert wellbeing.get_state().continuous_usage_seconds == 0

    clock.advance(minutes=50)
    wellbeing.start_break()
    clock.advance(minutes=2)
    second_break = wellbeing.complete_break()
    assert second_break.completion_type == BreakCompletionType.MANUAL
    assert second_break.duration_seconds == 120
    assert wellbeing.get_state().continuous_usage_seconds == 0

    clock.advance(minutes=20)
    ended = sessions.end_session()

    persisted_breaks = breaks.get_breaks_by_session(session.id)
    events = breaks.get_by_session(session.id)
    summary = analytics.session_summary(ended)
    stats = analytics.period_stats(user.id, 7, clock.current + timedelta(seconds=1))

    assert ended.duration_seconds == 8220
    assert [item.duration_seconds for item in persisted_breaks] == [300, 120]
    assert [item.completion_type for item in persisted_breaks] == [
        BreakCompletionType.AUTOMATIC,
        BreakCompletionType.MANUAL,
    ]
    assert [event.event_type for event in events] == [
        BreakEventType.BREAK_POSTPONED,
        BreakEventType.BREAK_STARTED,
        BreakEventType.BREAK_STARTED,
    ]
    assert summary.completed_breaks == 2
    assert summary.postponed_breaks == 1
    assert summary.break_seconds == 420
    assert summary.work_seconds == 7800
    assert stats.session_count == 1
    assert stats.completed_breaks == 2
    assert sessions.get_user_sessions(other_user.id) == []
