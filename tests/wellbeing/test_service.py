from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch
from wellbeing.service import WellbeingService
from wellbeing.models import BreakCompletionType, BreakEventType, CycleState
from wellbeing.repository import SQLiteBreakEventRepository
from database.connection import DatabaseManager
from sessions.models import Session
from app import config

@pytest.fixture
def mock_session_service():
    service = Mock()
    return service

@pytest.fixture
def wellbeing_service(mock_session_service):
    return WellbeingService(mock_session_service)

def test_initial_state_is_near_zero(wellbeing_service, mock_session_service):
    # Setup mock session
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    # Mock time to be just 2 seconds after start
    current_time = start_time + timedelta(seconds=2)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        state = wellbeing_service.get_state()
        assert state is not None
        assert state.session_elapsed_seconds == 2
        assert state.continuous_usage_seconds == 2

def test_continuous_time_increases(wellbeing_service, mock_session_service):
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    current_time = start_time + timedelta(minutes=10)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        state = wellbeing_service.get_state()
        assert state.continuous_usage_seconds == 600

def test_state_changes_to_break_due_soon(wellbeing_service, mock_session_service):
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    # 46 minutes in
    current_time = start_time + timedelta(minutes=46)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        cycle = wellbeing_service.get_cycle_state()
        assert cycle == CycleState.BREAK_DUE_SOON

def test_state_changes_to_break_due(wellbeing_service, mock_session_service):
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    # 51 minutes in
    current_time = start_time + timedelta(minutes=51)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        cycle = wellbeing_service.get_cycle_state()
        assert cycle == CycleState.BREAK_DUE

def test_time_until_next_break(wellbeing_service, mock_session_service):
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    # 10 minutes in
    current_time = start_time + timedelta(minutes=10)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        time_until = wellbeing_service.get_time_until_next_break()
        assert time_until == 40 * 60 # 40 minutes remaining

def test_service_works_without_advanced_fatigue(wellbeing_service, mock_session_service):
    # Just to prove it doesn't need FatigueEngine
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session = Session(id=1, user_id=1, started_at=start_time)
    mock_session_service.get_active_session.return_value = mock_session
    
    current_time = start_time + timedelta(minutes=10)
    with patch.object(wellbeing_service, '_get_current_time', return_value=current_time):
        state = wellbeing_service.get_state()
        assert state is not None


def _due_service(mock_session_service, repository=None):
    start_time = datetime(2026, 9, 28, 10, 0, 0)
    mock_session_service.get_active_session.return_value = Session(
        id=1, user_id=7, started_at=start_time
    )
    return WellbeingService(mock_session_service, repository), start_time


def test_break_due_generates_one_logical_reminder(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    now = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=now):
        assert service.should_show_reminder() is True
        assert service.should_show_reminder() is False
        assert service.is_reminder_active() is True


def test_postpone_keeps_continuous_usage_and_moves_next_reminder(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    due_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=due_at):
        service.should_show_reminder()
        before = service.get_state().continuous_usage_seconds
        service.postpone()

    five_minutes_later = due_at + timedelta(minutes=5)
    with patch.object(service, "_get_current_time", return_value=five_minutes_later):
        assert service.get_state().continuous_usage_seconds == before + 5 * 60
        assert service.get_time_until_next_break() == 5 * 60
        assert service.get_cycle_state() == CycleState.BREAK_DUE_SOON

    next_reminder = due_at + timedelta(minutes=config.POSTPONE_TIME_MINUTES)
    with patch.object(service, "_get_current_time", return_value=next_reminder):
        assert service.get_cycle_state() == CycleState.BREAK_DUE
        assert service.should_show_reminder() is True


def test_postpone_count_increases(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    first_due = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=first_due):
        service.postpone()
    second_due = first_due + timedelta(minutes=config.POSTPONE_TIME_MINUTES)
    with patch.object(service, "_get_current_time", return_value=second_due):
        service.postpone()
        assert service.get_state().postponed_breaks == 2


def test_start_break_sets_state_and_timestamp(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    now = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=now):
        service.start_break()
        assert service.get_cycle_state() == CycleState.BREAKING
        assert service.get_break_started_at() == now
        assert service.get_state().last_break_at == now


def test_breaking_freezes_continuous_usage_and_has_no_reminders(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()
        continuous_at_break = service.get_state().continuous_usage_seconds

    later = break_at + timedelta(minutes=1)
    with patch.object(service, "_get_current_time", return_value=later):
        state = service.get_state()
        assert state.continuous_usage_seconds == continuous_at_break
        assert state.session_elapsed_seconds == 51 * 60
        assert service.should_show_reminder() is False
        assert service.is_reminder_active() is False


def test_break_events_are_persisted(tmp_path, mock_session_service):
    db = DatabaseManager(str(tmp_path / "break-events.db"))
    db.initialize_database()
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users (id, name) VALUES (7, 'Ada')")
        conn.execute(
            "INSERT INTO sessions (id, user_id, started_at) VALUES (1, 7, ?)",
            ("2026-09-28T10:00:00",),
        )
        conn.commit()

    repository = SQLiteBreakEventRepository(db)
    service, started_at = _due_service(mock_session_service, repository)
    postponed_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=postponed_at):
        service.postpone()
    break_at = postponed_at + timedelta(minutes=config.POSTPONE_TIME_MINUTES)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()

    events = repository.get_by_session(1)
    assert [event.event_type for event in events] == [
        BreakEventType.BREAK_POSTPONED,
        BreakEventType.BREAK_STARTED,
    ]
    assert events[0].timestamp == postponed_at
    assert events[0].postpone_duration_minutes == config.POSTPONE_TIME_MINUTES
    assert events[1].timestamp == break_at
    assert all(event.user_id == 7 for event in events)


def test_break_timer_uses_timestamps(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()
        assert service.get_break_elapsed_seconds() == 0
        assert service.get_break_remaining_seconds() == 5 * 60

    later = break_at + timedelta(seconds=32)
    with patch.object(service, "_get_current_time", return_value=later):
        assert service.get_break_elapsed_seconds() == 32
        assert service.get_break_remaining_seconds() == 4 * 60 + 28


def test_break_finishes_automatically_and_schedules_next_reminder(
    mock_session_service,
):
    service, started_at = _due_service(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()

    completed_at = break_at + timedelta(minutes=5)
    with patch.object(service, "_get_current_time", return_value=completed_at):
        assert service.get_cycle_state() == CycleState.WORKING
        state = service.get_state()
        assert state.continuous_usage_seconds == 0
        assert state.continuous_usage_started_at == completed_at
        assert state.completed_breaks == 1
        assert service.get_time_until_next_break() == 50 * 60

    next_due = completed_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=next_due):
        assert service.get_cycle_state() == CycleState.BREAK_DUE


def test_break_finishes_manually_with_real_duration(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()

    completed_at = break_at + timedelta(seconds=73)
    with patch.object(service, "_get_current_time", return_value=completed_at):
        completed = service.complete_break()
        assert completed.duration_seconds == 73
        assert completed.completion_type == BreakCompletionType.MANUAL
        assert service.get_cycle_state() == CycleState.WORKING
        assert service.get_state().continuous_usage_seconds == 0


def test_cannot_start_more_than_one_active_break(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()
        original_started_at = service.get_break_started_at()
        service.start_break()
        assert service.get_break_started_at() == original_started_at
        assert service.get_cycle_state() == CycleState.BREAKING


def test_completing_nonexistent_break_is_harmless(mock_session_service):
    service, started_at = _due_service(mock_session_service)
    with patch.object(service, "_get_current_time", return_value=started_at):
        assert service.complete_break() is None
        assert service.get_cycle_state() == CycleState.WORKING


def test_session_end_closes_active_break(mock_session_service):
    callbacks = []
    mock_session_service.add_before_end_callback.side_effect = callbacks.append
    service, started_at = _due_service(mock_session_service)
    # Re-register because the fixture service is created after the side effect.
    service = WellbeingService(mock_session_service)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()
    ended_at = break_at + timedelta(seconds=20)
    with patch.object(service, "_get_current_time", return_value=ended_at):
        callbacks[-1]()
        assert service.get_cycle_state() == CycleState.WORKING
        assert service.get_state().continuous_usage_seconds == 0


def test_completed_break_persistence(tmp_path, mock_session_service):
    db = DatabaseManager(str(tmp_path / "completed-break.db"))
    db.initialize_database()
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users (id, name) VALUES (7, 'Ada')")
        conn.execute(
            "INSERT INTO sessions (id, user_id, started_at) VALUES (1, 7, ?)",
            ("2026-09-28T10:00:00",),
        )
        conn.commit()

    repository = SQLiteBreakEventRepository(db)
    service, started_at = _due_service(mock_session_service, repository)
    break_at = started_at + timedelta(minutes=50)
    with patch.object(service, "_get_current_time", return_value=break_at):
        service.start_break()
    completed_at = break_at + timedelta(seconds=84)
    with patch.object(service, "_get_current_time", return_value=completed_at):
        service.complete_break()

    saved = repository.get_breaks_by_session(1)
    assert len(saved) == 1
    assert saved[0].started_at == break_at
    assert saved[0].ended_at == completed_at
    assert saved[0].duration_seconds == 84
    assert saved[0].completion_type == BreakCompletionType.MANUAL
    assert repository.get_active_break(1) is None
