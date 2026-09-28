from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch
from wellbeing.service import WellbeingService
from wellbeing.models import CycleState
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
