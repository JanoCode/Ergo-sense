from domain.session import Session

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
