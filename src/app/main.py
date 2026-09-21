import sys
import os

# Permitir la ejecución directa con ``python src/app/main.py``.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database.connection import DatabaseManager
from users.repository import SQLiteUserRepository
from users.service import UserService
from sessions.repository import SQLiteSessionRepository
from sessions.service import SessionService
from monitoring.camera import CameraService
from monitoring.face_landmarks import FaceAnalyzer
from fatigue.repository import SQLiteBaselineRepository
from fatigue.service import BaselineService
from fatigue.history_repository import SQLiteFatigueHistoryRepository
from fatigue.history_service import FatigueHistoryService

def main():
    # Inicializar la base de datos al arrancar
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # Preparar dependencias
    user_repo = SQLiteUserRepository(db_manager)
    user_service = UserService(user_repo)
    
    session_repo = SQLiteSessionRepository(db_manager)
    session_service = SessionService(session_repo, user_service)
    
    camera_service = CameraService()
    face_analyzer = FaceAnalyzer()
    baseline_repo = SQLiteBaselineRepository(db_manager)
    baseline_service = BaselineService(baseline_repo)
    fatigue_history_service = FatigueHistoryService(
        SQLiteFatigueHistoryRepository(db_manager)
    )

    app = QApplication(sys.path)
    
    # Configuración global de la aplicación
    app.setApplicationName("ErgoSense")
    
    window = MainWindow(
        user_service, session_service, camera_service, face_analyzer,
        baseline_service, fatigue_history_service,
    )
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
