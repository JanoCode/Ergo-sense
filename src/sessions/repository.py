from typing import List

from sessions.models import Session

class SQLiteSessionRepository:
    def __init__(self, database_manager):
        self.db = database_manager

    def save(self, session: Session) -> Session:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            started_at_str = session.started_at.isoformat() if session.started_at else None
            ended_at_str = session.ended_at.isoformat() if session.ended_at else None
            
            if session.id is None:
                cursor.execute(
                    "INSERT INTO sessions (user_id, started_at, ended_at, duration_seconds) VALUES (?, ?, ?, ?)",
                    (session.user_id, started_at_str, ended_at_str, session.duration_seconds)
                )
                session.id = cursor.lastrowid
            else:
                cursor.execute(
                    "UPDATE sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?",
                    (ended_at_str, session.duration_seconds, session.id)
                )
            conn.commit()
            return session

    def get_by_user_id(self, user_id: int) -> List[Session]:
        sessions = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, user_id, started_at, ended_at, duration_seconds FROM sessions WHERE user_id = ? ORDER BY started_at DESC",
                (user_id,)
            )
            for row in cursor.fetchall():
                started_at = datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
                ended_at = datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None
                
                sessions.append(Session(
                    id=row["id"],
                    user_id=row["user_id"],
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_seconds=row["duration_seconds"]
                ))
        return sessions
