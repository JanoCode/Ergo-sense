from datetime import datetime, timedelta
from typing import Optional

from wellbeing.models import (
    BreakCompletionType,
    BreakEvent,
    BreakEventType,
    CycleState,
    WellbeingBreak,
    WellbeingSessionState,
)
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
        self._active_break: Optional[WellbeingBreak] = None
        self._last_break_completed_at: Optional[datetime] = None
        register_callback = getattr(
            self.session_service, "add_before_end_callback", None
        )
        if callable(register_callback):
            register_callback(self.end_active_break)

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
            self._active_break = (
                self.break_repository.get_active_break(active_session.id)
                if self.break_repository else None
            )
            if self._active_break:
                self._is_breaking = True
                self._break_started_at = self._active_break.started_at
                self._state.last_break_at = self._active_break.started_at

        # Update elapsed times
        self._state.session_elapsed_seconds = int(
            (now - self._state.session_started_at).total_seconds()
        )
        if not self._is_breaking:
            self._state.continuous_usage_seconds = int(
                (now - self._state.continuous_usage_started_at).total_seconds()
            )
        elif self.get_break_remaining_seconds(now) == 0:
            self._finish_break(now, BreakCompletionType.AUTOMATIC)

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

        active_session = self.session_service.get_active_session()
        if active_session:
            self._active_break = WellbeingBreak(
                session_id=active_session.id,
                user_id=active_session.user_id,
                started_at=now,
            )
            if self.break_repository:
                self._active_break = self.break_repository.start_break(
                    self._active_break
                )
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

    def get_break_elapsed_seconds(self, now: Optional[datetime] = None) -> int:
        if not self._is_breaking or not self._break_started_at:
            return 0
        current = now or self._get_current_time()
        return max(0, int((current - self._break_started_at).total_seconds()))

    def get_break_remaining_seconds(self, now: Optional[datetime] = None) -> int:
        duration = config.SUGGESTED_BREAK_DURATION_MINUTES * 60
        return max(0, duration - self.get_break_elapsed_seconds(now))

    def complete_break(self) -> Optional[WellbeingBreak]:
        """Complete an active break manually; harmless when none is active."""
        self._update_state()
        if not self._is_breaking:
            return None
        return self._finish_break(
            self._get_current_time(), BreakCompletionType.MANUAL
        )

    def end_active_break(self) -> Optional[WellbeingBreak]:
        """Close a break before its session is ended or the app exits."""
        return self.complete_break()

    def get_last_break_completed_at(self) -> Optional[datetime]:
        return self._last_break_completed_at

    def get_session_summary(self, session) -> dict:
        """Return simple break habits for a persisted session."""
        if not self.break_repository or session.id is None:
            return {
                "completed_breaks": 0,
                "postponed_breaks": 0,
                "total_break_seconds": 0,
                "max_continuous_usage_seconds": session.duration_seconds or 0,
            }

        breaks = self.break_repository.get_breaks_by_session(session.id)
        events = self.break_repository.get_by_session(session.id)
        completed = [item for item in breaks if item.ended_at is not None]
        postponed = sum(
            1 for event in events
            if event.event_type == BreakEventType.BREAK_POSTPONED
        )
        total_break = sum(item.duration_seconds or 0 for item in completed)

        cursor = session.started_at
        longest = 0
        for item in completed:
            if cursor and item.started_at:
                longest = max(
                    longest, int((item.started_at - cursor).total_seconds())
                )
            cursor = item.ended_at
        session_end = session.ended_at or self._get_current_time()
        if cursor and session_end:
            longest = max(longest, int((session_end - cursor).total_seconds()))

        return {
            "completed_breaks": len(completed),
            "postponed_breaks": postponed,
            "total_break_seconds": total_break,
            "max_continuous_usage_seconds": max(0, longest),
        }

    def was_break_completed_recently(self, seconds: int = 5) -> bool:
        if not self._last_break_completed_at:
            return False
        age = (
            self._get_current_time() - self._last_break_completed_at
        ).total_seconds()
        return 0 <= age < seconds

    def _finish_break(
        self, ended_at: datetime, completion_type: BreakCompletionType
    ) -> Optional[WellbeingBreak]:
        if not self._is_breaking or not self._break_started_at or not self._state:
            return None

        completed = self._active_break or WellbeingBreak(
            session_id=self._state.session_id,
            user_id=self.session_service.get_active_session().user_id,
            started_at=self._break_started_at,
        )
        completed.ended_at = ended_at
        completed.duration_seconds = max(
            0, int((ended_at - completed.started_at).total_seconds())
        )
        completed.completion_type = completion_type
        if self.break_repository and completed.id is not None:
            self.break_repository.complete_break(completed)

        self._is_breaking = False
        self._break_started_at = None
        self._active_break = None
        self._state.completed_breaks += 1
        self._state.continuous_usage_started_at = ended_at
        self._state.continuous_usage_seconds = 0
        self._reminder_shown = False
        self._next_reminder_at = None
        self._last_break_completed_at = ended_at
        return completed

    def _get_current_time(self) -> datetime:
        """Wrapper around datetime.now() to allow mocking in tests."""
        return datetime.now()
