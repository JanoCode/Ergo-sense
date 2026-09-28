from datetime import datetime
from typing import Callable

from wellbeing.models import BreakCompletionType


class WellbeingRecoveryService:
    """Reconcile records left open when the application did not shut down cleanly."""

    def __init__(
        self,
        session_repository,
        break_repository,
        now_provider: Callable[[], datetime] = datetime.now,
    ):
        self.session_repository = session_repository
        self.break_repository = break_repository
        self._now = now_provider

    def recover(self) -> tuple[int, int]:
        recovered_at = self._now()
        recovered_breaks = 0
        for wellbeing_break in self.break_repository.get_active_breaks():
            wellbeing_break.ended_at = max(
                recovered_at, wellbeing_break.started_at
            )
            wellbeing_break.duration_seconds = max(
                0,
                int(
                    (
                        wellbeing_break.ended_at - wellbeing_break.started_at
                    ).total_seconds()
                ),
            )
            wellbeing_break.completion_type = BreakCompletionType.MANUAL
            self.break_repository.complete_break(wellbeing_break)
            recovered_breaks += 1

        recovered_sessions = 0
        for session in self.session_repository.get_open_sessions():
            session.ended_at = max(recovered_at, session.started_at)
            session.duration_seconds = max(
                0, int((session.ended_at - session.started_at).total_seconds())
            )
            self.session_repository.save(session)
            recovered_sessions += 1

        return recovered_sessions, recovered_breaks
