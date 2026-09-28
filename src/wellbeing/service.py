from datetime import datetime
from typing import Optional

from wellbeing.models import WellbeingSessionState, CycleState
from sessions.service import SessionService
from app import config

class WellbeingService:
    def __init__(self, session_service: SessionService):
        self.session_service = session_service
        self._state: Optional[WellbeingSessionState] = None

    def get_state(self) -> Optional[WellbeingSessionState]:
        self._update_state()
        return self._state

    def _update_state(self):
        active_session = self.session_service.get_active_session()
        
        if not active_session:
            self._state = None
            return

        now = self._get_current_time()
        
        if not self._state or self._state.session_id != active_session.id:
            self._state = WellbeingSessionState(
                session_id=active_session.id,
                session_started_at=active_session.started_at,
                continuous_usage_started_at=active_session.started_at
            )

        # Update elapsed times
        self._state.session_elapsed_seconds = int((now - self._state.session_started_at).total_seconds())
        self._state.continuous_usage_seconds = int((now - self._state.continuous_usage_started_at).total_seconds())

    def get_cycle_state(self) -> CycleState:
        self._update_state()
        if not self._state:
            return CycleState.WORKING
            
        continuous_minutes = self._state.continuous_usage_seconds / 60.0
        
        if continuous_minutes >= config.RECOMMENDED_BREAK_INTERVAL_MINUTES:
            return CycleState.BREAK_DUE
        elif continuous_minutes >= (config.RECOMMENDED_BREAK_INTERVAL_MINUTES - config.BREAK_WARNING_ADVANCE_MINUTES):
            return CycleState.BREAK_DUE_SOON
            
        return CycleState.WORKING

    def get_time_until_next_break(self) -> int:
        self._update_state()
        if not self._state:
            return config.RECOMMENDED_BREAK_INTERVAL_MINUTES * 60
            
        remaining = (config.RECOMMENDED_BREAK_INTERVAL_MINUTES * 60) - self._state.continuous_usage_seconds
        return max(0, remaining)

    def _get_current_time(self) -> datetime:
        """Wrapper around datetime.now() to allow mocking in tests."""
        return datetime.now()
