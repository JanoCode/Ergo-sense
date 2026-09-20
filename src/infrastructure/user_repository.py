from domain.user import User

class SQLiteUserRepository:
    def __init__(self, database_manager):
        self.db = database_manager

    def save(self, user: User) -> User:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name) VALUES (?)",
                (user.name,)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            # Recuperar el usuario con los campos autogenerados
            cursor.execute("SELECT id, name, created_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            return User(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"]
            )
