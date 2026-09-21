"""Exercise real SQLite rows through the redesigned UI, including restart."""
import gc
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from database.connection import DatabaseManager
from users.repository import SQLiteUserRepository
from users.service import UserService
from sessions.repository import SQLiteSessionRepository
from sessions.service import SessionService
from ui.main_window import MainWindow


class PersistedUsersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_existing_users_survive_initialization_selection_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.db"
            db = DatabaseManager(path)
            db.initialize_database()
            with sqlite3.connect(path) as conn:
                conn.execute("INSERT INTO users(id,name,created_at) VALUES(17, 'Alejandro Silva', '2026-09-21 02:22:48')")
                conn.commit()
            conn.close()
            for restart in range(2):
                db = DatabaseManager(path)
                db.initialize_database()
                users = UserService(SQLiteUserRepository(db))
                sessions = SessionService(SQLiteSessionRepository(db), users)
                window = MainWindow(users, sessions)
                view = window.dashboard
                view._navigate(view.PAGE_USERS)
                names = [label.text() for label in view.findChildren(QLabel)]
                self.assertIn("Alejandro Silva", names)
                self.assertIn("Creado: 21/09/2026", names)
                card = next(
                    view.users_list_layout.itemAt(index).widget()
                    for index in range(view.users_list_layout.count() - 1)
                    if any(label.text() == "Alejandro Silva" for label in
                           view.users_list_layout.itemAt(index).widget().findChildren(QLabel))
                )
                card.findChild(QPushButton).click()
                self.assertEqual(users.get_active_user().id, 17)
                self.assertIn("Alejandro Silva", view.lbl_active_user.text())
                if restart == 0:
                    sessions.start_session()
                    sessions.end_session()
                    users.create_user("Nuevo perfil de prueba")
                    view._navigate(view.PAGE_HOME)
                    view._navigate(view.PAGE_USERS)
                    self.assertEqual(view.users_list_layout.count(), 3)
                self.assertEqual(len(sessions.get_user_sessions(17)), 1)
                window.close()
                window.deleteLater()
                self.app.processEvents()
            self.assertEqual([u.id for u in users.get_all_users()].count(17), 1)
            self.assertEqual(len(users.get_all_users()), 2)
            gc.collect()  # SQLite context managers commit but do not close connections.

    def test_database_path_does_not_depend_on_working_directory(self):
        expected = DatabaseManager().db_path
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(DatabaseManager().db_path, expected)
                self.assertTrue(expected.is_absolute())
                self.assertFalse((Path(directory) / "ergosense.db").exists())
            finally:
                os.chdir(original)

    def test_load_failure_is_not_reported_as_empty_database(self):
        users = UserService(None)
        with patch.object(users, "get_all_users", side_effect=sqlite3.OperationalError("test failure")):
            with self.assertLogs("ui.dashboard", level="ERROR"):
                window = MainWindow(users)
            labels = [label.text() for label in window.dashboard.findChildren(QLabel)]
            self.assertTrue(any("No se pudieron cargar" in text for text in labels))
            self.assertNotIn("No hay usuarios registrados.", labels)
            window.close()
            window.deleteLater()
