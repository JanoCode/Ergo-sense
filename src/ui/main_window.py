from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from ui.modern_dashboard import ModernDashboardWidget

class MainWindow(QMainWindow):
    def __init__(self, user_service=None, session_service=None, camera_service=None,
                 face_analyzer=None, baseline_service=None,
                 fatigue_history_service=None, fatigue_analytics_service=None):
        super().__init__()
        
        self.camera_service = camera_service
        self.setWindowTitle("ErgoSense - Monitoreo de Fatiga")
        self.setMinimumSize(760, 560)
        self.resize(1180, 760)
        
        # Configurar widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Cargar vista inicial (Dashboard)
        self.dashboard = ModernDashboardWidget(
            user_service, session_service, camera_service, face_analyzer,
            baseline_service, fatigue_history_service, fatigue_analytics_service,
        )
        self.main_layout.addWidget(self.dashboard)

    def closeEvent(self, event):
        self.dashboard.shutdown()
        if self.camera_service:
            self.camera_service.stop()
        super().closeEvent(event)
