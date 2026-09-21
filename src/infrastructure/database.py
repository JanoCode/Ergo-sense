import sqlite3
from contextlib import closing
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
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            
            # Crear tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crear tabla de sesiones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration_seconds INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            
            # Crear tabla de baselines personales
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    state TEXT NOT NULL DEFAULT 'INSUFFICIENT_DATA',
                    ear_mean REAL, ear_std REAL, ear_samples INTEGER,
                    blink_rate_mean REAL, blink_rate_std REAL, blink_rate_samples INTEGER,
                    blink_duration_mean REAL, blink_duration_std REAL, blink_duration_samples INTEGER,
                    perclos_mean REAL, perclos_std REAL, perclos_samples INTEGER,
                    mar_mean REAL, mar_std REAL, mar_samples INTEGER,
                    pitch_mean REAL, pitch_std REAL, pitch_samples INTEGER,
                    yaw_mean REAL, yaw_std REAL, yaw_samples INTEGER,
                    roll_mean REAL, roll_std REAL, roll_samples INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')

            conn.commit()
