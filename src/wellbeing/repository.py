from contextlib import closing
from typing import List
from datetime import datetime

from wellbeing.models import BreakEvent, BreakEventType


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
