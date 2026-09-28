from contextlib import closing
from typing import List
from datetime import datetime

from wellbeing.models import (
    BreakCompletionType,
    BreakEvent,
    BreakEventType,
    WellbeingBreak,
)


class SQLiteBreakEventRepository:
    """Persists break-related events (started, postponed)."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def save(self, event: BreakEvent) -> BreakEvent:
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.cursor()
            ts = event.timestamp or datetime.now()
            cursor.execute(
                """INSERT INTO break_events
                   (session_id, user_id, event_type, timestamp, postpone_duration_minutes)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    event.session_id,
                    event.user_id,
                    event.event_type.value,
                    ts.isoformat(),
                    event.postpone_duration_minutes,
                ),
            )
            conn.commit()
            event.id = cursor.lastrowid
            event.timestamp = ts
            return event

    def get_by_session(self, session_id: int) -> List[BreakEvent]:
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM break_events WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_event(row) for row in rows]

    def start_break(self, wellbeing_break: WellbeingBreak) -> WellbeingBreak:
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO wellbeing_breaks
                   (session_id, user_id, started_at)
                   VALUES (?, ?, ?)""",
                (
                    wellbeing_break.session_id,
                    wellbeing_break.user_id,
                    wellbeing_break.started_at.isoformat(),
                ),
            )
            conn.commit()
            wellbeing_break.id = cursor.lastrowid
            return wellbeing_break

    def complete_break(self, wellbeing_break: WellbeingBreak) -> WellbeingBreak:
        if wellbeing_break.id is None:
            raise ValueError("No se puede completar una pausa sin persistir.")
        with closing(self.db_manager.get_connection()) as conn:
            conn.execute(
                """UPDATE wellbeing_breaks
                   SET ended_at = ?, duration_seconds = ?, completion_type = ?
                   WHERE id = ? AND ended_at IS NULL""",
                (
                    wellbeing_break.ended_at.isoformat(),
                    wellbeing_break.duration_seconds,
                    wellbeing_break.completion_type.value,
                    wellbeing_break.id,
                ),
            )
            conn.commit()
        return wellbeing_break

    def get_active_break(self, session_id: int) -> WellbeingBreak | None:
        with closing(self.db_manager.get_connection()) as conn:
            row = conn.execute(
                """SELECT * FROM wellbeing_breaks
                   WHERE session_id = ? AND ended_at IS NULL
                   ORDER BY started_at DESC LIMIT 1""",
                (session_id,),
            ).fetchone()
            return self._row_to_break(row) if row else None

    def get_breaks_by_session(self, session_id: int) -> List[WellbeingBreak]:
        with closing(self.db_manager.get_connection()) as conn:
            rows = conn.execute(
                """SELECT * FROM wellbeing_breaks
                   WHERE session_id = ? ORDER BY started_at""",
                (session_id,),
            ).fetchall()
            return [self._row_to_break(row) for row in rows]

    @staticmethod
    def _row_to_event(row) -> BreakEvent:
        return BreakEvent(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            event_type=BreakEventType(row["event_type"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            postpone_duration_minutes=row["postpone_duration_minutes"],
        )

    @staticmethod
    def _row_to_break(row) -> WellbeingBreak:
        return WellbeingBreak(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=(
                datetime.fromisoformat(row["ended_at"])
                if row["ended_at"] else None
            ),
            duration_seconds=row["duration_seconds"],
            completion_type=(
                BreakCompletionType(row["completion_type"])
                if row["completion_type"] else None
            ),
        )
