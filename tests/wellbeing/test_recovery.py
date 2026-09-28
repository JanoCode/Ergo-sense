from datetime import datetime, timedelta

from database.connection import DatabaseManager
from sessions.models import Session
from sessions.repository import SQLiteSessionRepository
from wellbeing.models import BreakCompletionType, WellbeingBreak
from wellbeing.recovery import WellbeingRecoveryService
from wellbeing.repository import SQLiteBreakEventRepository


def test_recovery_closes_only_records_left_open(tmp_path):
    database = DatabaseManager(str(tmp_path / "recovery.db"))
    database.initialize_database()
    sessions = SQLiteSessionRepository(database)
    breaks = SQLiteBreakEventRepository(database)
    started_at = datetime(2026, 9, 28, 8, 0, 0)
    recovered_at = started_at + timedelta(hours=1)

    open_session = sessions.save(Session(user_id=1, started_at=started_at))
    open_break = breaks.start_break(
        WellbeingBreak(
            session_id=open_session.id,
            user_id=1,
            started_at=started_at + timedelta(minutes=50),
        )
    )
    completed_session = sessions.save(
        Session(
            user_id=1,
            started_at=started_at - timedelta(hours=2),
            ended_at=started_at - timedelta(hours=1),
            duration_seconds=3600,
        )
    )
    completed_break = breaks.start_break(
        WellbeingBreak(
            session_id=completed_session.id,
            user_id=1,
            started_at=started_at - timedelta(hours=1, minutes=10),
        )
    )
    completed_break.ended_at = started_at - timedelta(hours=1)
    completed_break.duration_seconds = 600
    completed_break.completion_type = BreakCompletionType.AUTOMATIC
    breaks.complete_break(completed_break)

    recovered = WellbeingRecoveryService(
        sessions, breaks, lambda: recovered_at
    ).recover()

    assert recovered == (1, 1)
    recovered_session = sessions.get_by_user_id(1)[0]
    recovered_break = breaks.get_breaks_by_session(open_session.id)[0]
    untouched_break = breaks.get_breaks_by_session(completed_session.id)[0]
    assert recovered_session.ended_at == recovered_at
    assert recovered_session.duration_seconds == 3600
    assert recovered_break.id == open_break.id
    assert recovered_break.ended_at == recovered_at
    assert recovered_break.duration_seconds == 600
    assert recovered_break.completion_type == BreakCompletionType.MANUAL
    assert untouched_break.ended_at == completed_break.ended_at
    assert WellbeingRecoveryService(
        sessions, breaks, lambda: recovered_at
    ).recover() == (0, 0)


def test_recovery_never_creates_negative_durations(tmp_path):
    database = DatabaseManager(str(tmp_path / "future-records.db"))
    database.initialize_database()
    sessions = SQLiteSessionRepository(database)
    breaks = SQLiteBreakEventRepository(database)
    now = datetime(2026, 9, 28, 8, 0, 0)
    future = now + timedelta(minutes=5)
    session = sessions.save(Session(user_id=1, started_at=future))
    breaks.start_break(
        WellbeingBreak(session_id=session.id, user_id=1, started_at=future)
    )

    WellbeingRecoveryService(sessions, breaks, lambda: now).recover()

    recovered_session = sessions.get_by_user_id(1)[0]
    recovered_break = breaks.get_breaks_by_session(session.id)[0]
    assert recovered_session.ended_at == future
    assert recovered_session.duration_seconds == 0
    assert recovered_break.ended_at == future
    assert recovered_break.duration_seconds == 0
