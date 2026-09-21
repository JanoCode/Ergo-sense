import json
from contextlib import closing
from typing import List, Optional, Tuple

from fatigue.models import (
    FatigueEvent, FatigueEventType, FatigueLevel, SessionFatigueSummary,
    StoredFatigueAssessment,
)


class SQLiteFatigueHistoryRepository:
    """Persistencia SQLite de evaluaciones, eventos y resúmenes de fatiga."""

    def __init__(self, database_manager):
        self.db = database_manager

    def save_assessment(
        self, assessment: StoredFatigueAssessment
    ) -> Tuple[StoredFatigueAssessment, bool]:
        with closing(self.db.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO fatigue_assessments (
                    session_id, user_id, timestamp, score, level, confidence,
                    active_signals, unavailable_signals, reasons, perclos,
                    head_deviation_degrees
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment.session_id, assessment.user_id, assessment.timestamp,
                assessment.score, assessment.level.value, assessment.confidence,
                json.dumps(assessment.active_signals, ensure_ascii=False),
                json.dumps(assessment.unavailable_signals, ensure_ascii=False),
                json.dumps(assessment.reasons, ensure_ascii=False),
                assessment.perclos, assessment.head_deviation_degrees,
            ))
            inserted = cursor.rowcount == 1
            if inserted:
                assessment.id = cursor.lastrowid
            else:
                cursor.execute(
                    "SELECT id FROM fatigue_assessments WHERE session_id = ? AND timestamp = ?",
                    (assessment.session_id, assessment.timestamp),
                )
                assessment.id = cursor.fetchone()["id"]
            conn.commit()
        return assessment, inserted

    def get_assessments(self, session_id: int) -> List[StoredFatigueAssessment]:
        with closing(self.db.get_connection()) as conn:
            rows = conn.execute('''
                SELECT * FROM fatigue_assessments
                WHERE session_id = ? ORDER BY timestamp ASC
            ''', (session_id,)).fetchall()
        return [self._assessment_from_row(row) for row in rows]

    def save_event(self, event: FatigueEvent) -> Tuple[FatigueEvent, bool]:
        with closing(self.db.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO fatigue_events (
                    session_id, user_id, event_type, timestamp, data_json
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                event.session_id, event.user_id, event.event_type.value,
                event.timestamp, json.dumps(event.data, ensure_ascii=False),
            ))
            inserted = cursor.rowcount == 1
            if inserted:
                event.id = cursor.lastrowid
            else:
                cursor.execute('''
                    SELECT id FROM fatigue_events
                    WHERE session_id = ? AND event_type = ? AND timestamp = ?
                ''', (event.session_id, event.event_type.value, event.timestamp))
                event.id = cursor.fetchone()["id"]
            conn.commit()
        return event, inserted

    def get_events(
        self, session_id: int, event_type: Optional[FatigueEventType] = None
    ) -> List[FatigueEvent]:
        query = "SELECT * FROM fatigue_events WHERE session_id = ?"
        params = [session_id]
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type.value)
        query += " ORDER BY timestamp ASC, id ASC"
        with closing(self.db.get_connection()) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._event_from_row(row) for row in rows]

    def save_summary(self, summary: SessionFatigueSummary) -> SessionFatigueSummary:
        with closing(self.db.get_connection()) as conn:
            conn.execute('''
                INSERT INTO fatigue_session_summaries (
                    session_id, user_id, duration_seconds, total_blinks,
                    average_blink_rate, average_blink_duration, average_perclos,
                    max_perclos, prolonged_closures, yawns,
                    max_head_deviation_degrees, average_score, max_score, max_level,
                    time_to_mild_seconds, time_to_moderate_seconds,
                    time_to_high_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    duration_seconds=excluded.duration_seconds,
                    total_blinks=excluded.total_blinks,
                    average_blink_rate=excluded.average_blink_rate,
                    average_blink_duration=excluded.average_blink_duration,
                    average_perclos=excluded.average_perclos,
                    max_perclos=excluded.max_perclos,
                    prolonged_closures=excluded.prolonged_closures,
                    yawns=excluded.yawns,
                    max_head_deviation_degrees=excluded.max_head_deviation_degrees,
                    average_score=excluded.average_score,
                    max_score=excluded.max_score,
                    max_level=excluded.max_level,
                    time_to_mild_seconds=excluded.time_to_mild_seconds,
                    time_to_moderate_seconds=excluded.time_to_moderate_seconds,
                    time_to_high_seconds=excluded.time_to_high_seconds,
                    updated_at=CURRENT_TIMESTAMP
            ''', (
                summary.session_id, summary.user_id, summary.duration_seconds,
                summary.total_blinks, summary.average_blink_rate,
                summary.average_blink_duration, summary.average_perclos,
                summary.max_perclos, summary.prolonged_closures, summary.yawns,
                summary.max_head_deviation_degrees, summary.average_score,
                summary.max_score,
                summary.max_level.value if summary.max_level else None,
                summary.time_to_mild_seconds, summary.time_to_moderate_seconds,
                summary.time_to_high_seconds,
            ))
            conn.commit()
        return summary

    def get_summary(self, session_id: int) -> Optional[SessionFatigueSummary]:
        with closing(self.db.get_connection()) as conn:
            row = conn.execute(
                "SELECT * FROM fatigue_session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionFatigueSummary(
            session_id=row["session_id"], user_id=row["user_id"],
            duration_seconds=row["duration_seconds"],
            total_blinks=row["total_blinks"],
            average_blink_rate=row["average_blink_rate"],
            average_blink_duration=row["average_blink_duration"],
            average_perclos=row["average_perclos"],
            max_perclos=row["max_perclos"],
            prolonged_closures=row["prolonged_closures"], yawns=row["yawns"],
            max_head_deviation_degrees=row["max_head_deviation_degrees"],
            average_score=row["average_score"], max_score=row["max_score"],
            max_level=FatigueLevel(row["max_level"]) if row["max_level"] else None,
            time_to_mild_seconds=row["time_to_mild_seconds"],
            time_to_moderate_seconds=row["time_to_moderate_seconds"],
            time_to_high_seconds=row["time_to_high_seconds"],
        )

    @staticmethod
    def _assessment_from_row(row) -> StoredFatigueAssessment:
        return StoredFatigueAssessment(
            id=row["id"], session_id=row["session_id"], user_id=row["user_id"],
            timestamp=row["timestamp"], score=row["score"],
            level=FatigueLevel(row["level"]), confidence=row["confidence"],
            active_signals=json.loads(row["active_signals"]),
            unavailable_signals=json.loads(row["unavailable_signals"]),
            reasons=json.loads(row["reasons"]), perclos=row["perclos"],
            head_deviation_degrees=row["head_deviation_degrees"],
        )

    @staticmethod
    def _event_from_row(row) -> FatigueEvent:
        return FatigueEvent(
            id=row["id"], session_id=row["session_id"], user_id=row["user_id"],
            event_type=FatigueEventType(row["event_type"]),
            timestamp=row["timestamp"], data=json.loads(row["data_json"]),
        )
