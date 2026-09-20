from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
from PySide6.QtCore import Qt

class DashboardWidget(QWidget):
    def __init__(self, user_service=None):
        super().__init__()
        self.user_service = user_service
        self._setup_ui()
        self._load_users()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 1. Cabecera con Nombre de la App
        header_layout = QHBoxLayout()
        app_title = QLabel("ErgoSense")
        app_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(app_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 2. Área central
        central_layout = QHBoxLayout()
        central_layout.setSpacing(20)
        
        # Columna Izquierda (Estado + Usuarios)
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        
        # Panel de Estado
        status_panel = QFrame()
        status_panel.setFrameShape(QFrame.StyledPanel)
        status_panel.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0;")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(20, 20, 20, 20)
        
        status_title = QLabel("Estado de Monitoreo")
        status_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        status_layout.addWidget(status_title)
        
        self.lbl_status = QLabel("Inactivo")
        self.lbl_status.setStyleSheet("font-size: 16px; color: #7f8c8d; border: none;")
        status_layout.addWidget(self.lbl_status)
        
        status_layout.addSpacing(10)
        
        self.btn_start_monitoring = QPushButton("Iniciar monitoreo")
        self.btn_start_monitoring.setMinimumHeight(40)
        self.btn_start_monitoring.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        status_layout.addWidget(self.btn_start_monitoring)
        left_column.addWidget(status_panel)
        
        # Panel de Usuarios
        users_panel = QFrame()
        users_panel.setFrameShape(QFrame.StyledPanel)
        users_panel.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0;")
        users_layout = QVBoxLayout(users_panel)
        users_layout.setContentsMargins(20, 20, 20, 20)
        
        users_title_layout = QHBoxLayout()
        users_title = QLabel("Usuarios Registrados")
        users_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        users_title_layout.addWidget(users_title)
        users_title_layout.addStretch()
        
        self.btn_create_user = QPushButton("Crear usuario")
        self.btn_create_user.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.btn_create_user.clicked.connect(self._show_create_user_dialog)
        users_title_layout.addWidget(self.btn_create_user)
        
        users_layout.addLayout(users_title_layout)
        
        # Scroll area para los usuarios
        self.users_scroll = QScrollArea()
        self.users_scroll.setWidgetResizable(True)
        self.users_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.users_container = QWidget()
        self.users_container.setStyleSheet("background-color: transparent;")
        self.users_list_layout = QVBoxLayout(self.users_container)
        self.users_list_layout.setContentsMargins(0, 0, 0, 0)
        self.users_list_layout.setSpacing(10)
        self.users_list_layout.addStretch() # Mantener siempre al fondo
        
        self.users_scroll.setWidget(self.users_container)
        users_layout.addWidget(self.users_scroll)
        
        left_column.addWidget(users_panel)
        
        # Panel Derecho (Historial)
        history_panel = QFrame()
        history_panel.setFrameShape(QFrame.StyledPanel)
        history_panel.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0;")
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(20, 20, 20, 20)
        
        history_title = QLabel("Historial (Próximamente)")
        history_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        history_layout.addWidget(history_title)
        
        empty_history_lbl = QLabel("No hay datos históricos disponibles.")
        empty_history_lbl.setStyleSheet("color: #95a5a6; font-style: italic; border: none;")
        empty_history_lbl.setAlignment(Qt.AlignCenter)
        
        history_layout.addStretch()
        history_layout.addWidget(empty_history_lbl)
        history_layout.addStretch()
        
        # Añadir paneles al layout central
        central_layout.addLayout(left_column, 1) # Proporción 1
        central_layout.addWidget(history_panel, 2) # Proporción 2
        
        layout.addLayout(central_layout)

    def _load_users(self):
        # Limpiar layout actual de usuarios si hubiera (manteniendo el stretch final)
        while self.users_list_layout.count() > 1:
            item = self.users_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.user_service:
            self._show_empty_users_message()
            return
            
        try:
            users = self.user_service.get_all_users()
            if not users:
                self._show_empty_users_message()
            else:
                for user in users:
                    user_widget = self._create_user_widget(user)
                    # Insertar antes del stretch (que está al final)
                    self.users_list_layout.insertWidget(self.users_list_layout.count() - 1, user_widget)
        except Exception as e:
            self._show_empty_users_message()

    def _show_empty_users_message(self):
        empty_lbl = QLabel("No hay usuarios registrados.")
        empty_lbl.setStyleSheet("color: #95a5a6; font-style: italic; border: none; padding: 10px;")
        empty_lbl.setAlignment(Qt.AlignCenter)
        self.users_list_layout.insertWidget(0, empty_lbl)

    def _create_user_widget(self, user):
        widget = QFrame()
        widget.setStyleSheet("background-color: white; border-radius: 4px; padding: 8px; border: 1px solid #dcdde1;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)
        
        name_lbl = QLabel(user.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        date_lbl = QLabel(f"Creado: {user.created_at}")
        date_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; border: none;")
        
        layout.addWidget(name_lbl)
        layout.addWidget(date_lbl)
        return widget

    def _show_create_user_dialog(self):
        from presentation.user_dialog import CreateUserDialog
        if not self.user_service:
            return
            
        dialog = CreateUserDialog(self.user_service, self)
        if dialog.exec():
            self._load_users()
