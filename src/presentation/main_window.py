from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from presentation.dashboard import DashboardWidget

class MainWindow(QMainWindow):
    def __init__(self, user_service=None):
        super().__init__()
        
        self.setWindowTitle("ErgoSense - Monitoreo de Fatiga")
        self.resize(1024, 768)
        
        # Configurar widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cargar vista inicial (Dashboard)
        self.dashboard = DashboardWidget(user_service)
        self.main_layout.addWidget(self.dashboard)
