import sys
import os

# Asegurar que el directorio 'src' esté en el path para importar los módulos correctamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from presentation.main_window import MainWindow

def main():
    app = QApplication(sys.path)
    
    # Configuración global de la aplicación
    app.setApplicationName("ErgoSense")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
