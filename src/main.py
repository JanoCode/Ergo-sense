import sys
import os

# Asegurar que el directorio 'src' esté en el path para importar los módulos correctamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from presentation.main_window import MainWindow
from infrastructure.database import DatabaseManager
from infrastructure.user_repository import SQLiteUserRepository
from application.user_service import UserService
from infrastructure.session_repository import SQLiteSessionRepository
from application.session_service import SessionService

def main():
    # Inicializar la base de datos al arrancar
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # Preparar dependencias
    user_repo = SQLiteUserRepository(db_manager)
    user_service = UserService(user_repo)
    
    session_repo = SQLiteSessionRepository(db_manager)
    session_service = SessionService(session_repo, user_service)

    app = QApplication(sys.path)
    
    # Configuración global de la aplicación
    app.setApplicationName("ErgoSense")
    
    window = MainWindow(user_service, session_service)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
