import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

from domain.user import User
from infrastructure.database import DatabaseManager
from infrastructure.user_repository import SQLiteUserRepository

class TestUserRepository(unittest.TestCase):
    def setUp(self):
        # Usar base de datos en memoria para los tests
        self.db = DatabaseManager(":memory:")
        # Limpiar BD si es compartida
        with self.db.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS users")
        self.db.initialize_database()
        self.repo = SQLiteUserRepository(self.db)

    def test_save_user(self):
        user = User(name="Ana Gomez")
        saved_user = self.repo.save(user)
        
        self.assertIsNotNone(saved_user.id)
        self.assertEqual(saved_user.name, "Ana Gomez")
        self.assertIsNotNone(saved_user.created_at)
        
        # Verificar directamente en la base de datos
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            count = cursor.fetchone()["count"]
            self.assertEqual(count, 1)

    def test_get_all_users(self):
        self.repo.save(User(name="User 1"))
        self.repo.save(User(name="User 2"))
        
        users = self.repo.get_all()
        self.assertEqual(len(users), 2)

if __name__ == '__main__':
    unittest.main()
