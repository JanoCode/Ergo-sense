import sqlite3
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_name="ergosense.db"):
        self.is_memory = (db_name == ":memory:")
        if self.is_memory:
            self.db_path = "file::memory:?cache=shared"
        else:
            # Almacenamos la base de datos en el directorio raíz del proyecto
            base_dir = Path(__file__).parent.parent.parent
            self.db_path = base_dir / db_name

    def get_connection(self):
        """Retorna una conexión a la base de datos SQLite."""
        if self.is_memory:
            conn = sqlite3.connect(self.db_path, uri=True)
        else:
            conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Crea la base de datos y las tablas necesarias si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
