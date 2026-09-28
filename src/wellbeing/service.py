from datetime import datetime, timedelta
from typing import Optional

from wellbeing.models import WellbeingSessionState, CycleState, BreakEvent, BreakEventType
from sessions.service import SessionService
from app import config


class WellbeingService:
    def __init__(self, session_service: SessionService, break_repository=None):
        self.session_service = session_service
        self.break_repository = break_repository
        self._state: Optional[WellbeingSessionState] = None
        self._is_breaking: bool = False
        self._break_started_at: Optional[datetime] = None
        self._reminder_shown: bool = False
        self._next_reminder_at: Optional[datetime] = None

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
                continuous_usage_started_at=active_session.started_at,
            )
            self._is_breaking = False
            self._break_started_at = None
            self._reminder_shown = False
            self._next_reminder_at = None

        # Update elapsed times
        self._state.session_elapsed_seconds = int(
            (now - self._state.session_started_at).total_seconds()
        )
        if not self._is_breaking:
            self._state.continuous_usage_seconds = int(
                (now - self._state.continuous_usage_started_at).total_seconds()
            )

    def get_cycle_state(self) -> CycleState:
        self._update_state()
        if not self._state:
            return CycleState.WORKING

        if self._is_breaking:
            return CycleState.BREAKING

        continuous_minutes = self._state.continuous_usage_seconds / 60.0
        effective_threshold = config.RECOMMENDED_BREAK_INTERVAL_MINUTES

        # If a postponement pushed the threshold, use that
        if self._next_reminder_at:
            now = self._get_current_time()
            if now < self._next_reminder_at:
                remaining = (self._next_reminder_at - now).total_seconds()
                effective_threshold = (
                    self._state.continuous_usage_seconds + remaining
                ) / 60.0

        if continuous_minutes >= effective_threshold:
            return CycleState.BREAK_DUE
        elif continuous_minutes >= (
            effective_threshold - config.BREAK_WARNING_ADVANCE_MINUTES
        ):
            return CycleState.BREAK_DUE_SOON

        return CycleState.WORKING

    def get_time_until_next_break(self) -> int:
        self._update_state()
        if not self._state:
            return config.RECOMMENDED_BREAK_INTERVAL_MINUTES * 60

        if self._is_breaking:
            return 0

        if self._next_reminder_at:
            now = self._get_current_time()
            if now < self._next_reminder_at:
                return max(0, int((self._next_reminder_at - now).total_seconds()))

        remaining = (
            config.RECOMMENDED_BREAK_INTERVAL_MINUTES * 60
        ) - self._state.continuous_usage_seconds
        return max(0, remaining)

    def should_show_reminder(self) -> bool:
        """Returns True only once when BREAK_DUE is first reached."""
        cycle = self.get_cycle_state()
        if cycle == CycleState.BREAK_DUE and not self._reminder_shown:
            self._reminder_shown = True
            return True
        return False

    def is_reminder_active(self) -> bool:
        """True while the user hasn't acted on the current reminder."""
        cycle = self.get_cycle_state()
        return cycle == CycleState.BREAK_DUE and self._reminder_shown

    def postpone(self) -> None:
        """Postpone the break reminder by the configured duration."""
        self._update_state()
        if not self._state or self._is_breaking or self.get_cycle_state() != CycleState.BREAK_DUE:
            return

        now = self._get_current_time()
        self._state.postponed_breaks += 1
        self._next_reminder_at = now + timedelta(
            minutes=config.POSTPONE_TIME_MINUTES
        )
        self._reminder_shown = False

        if self.break_repository:
            active_session = self.session_service.get_active_session()
            if active_session:
                self.break_repository.save(
                    BreakEvent(
                        session_id=active_session.id,
                        user_id=active_session.user_id,
                        event_type=BreakEventType.BREAK_POSTPONED,
                        timestamp=now,
                        postpone_duration_minutes=config.POSTPONE_TIME_MINUTES,
                    )
                )

    def start_break(self) -> None:
        """Transition to BREAKING state."""
        self._update_state()
        if not self._state or self._is_breaking or self.get_cycle_state() != CycleState.BREAK_DUE:
            return

        now = self._get_current_time()
        self._is_breaking = True
        self._break_started_at = now
        self._state.last_break_at = now
        self._reminder_shown = False
        self._next_reminder_at = None

        if self.break_repository:
            active_session = self.session_service.get_active_session()
            if active_session:
                self.break_repository.save(
                    BreakEvent(
                        session_id=active_session.id,
                        user_id=active_session.user_id,
                        event_type=BreakEventType.BREAK_STARTED,
                        timestamp=now,
                    )
                )

    def get_break_started_at(self) -> Optional[datetime]:
        return self._break_started_at

    def _get_current_time(self) -> datetime:
        """Wrapper around datetime.now() to allow mocking in tests."""
        return datetime.now()
