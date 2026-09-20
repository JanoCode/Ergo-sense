from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QScrollArea, QMessageBox
from PySide6.QtCore import Qt, QTimer
from datetime import datetime

class DashboardWidget(QWidget):
    def __init__(self, user_service=None, session_service=None):
        super().__init__()
        self.user_service = user_service
        self.session_service = session_service
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_session_time)
        
        self._setup_ui()
        self._load_users()
        self._update_active_user_display()
        
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
        
        self.lbl_active_user = QLabel("No hay usuario activo")
        self.lbl_active_user.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c; border: none;")
        status_layout.addWidget(self.lbl_active_user)
        
        status_layout.addSpacing(10)
        
        status_title = QLabel("Estado de Monitoreo")
        status_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        status_layout.addWidget(status_title)
        
        self.lbl_status = QLabel("Inactivo")
        self.lbl_status.setStyleSheet("font-size: 16px; color: #7f8c8d; border: none;")
        status_layout.addWidget(self.lbl_status)
        
        self.lbl_elapsed = QLabel("Transcurrido: 00:00:00")
        self.lbl_elapsed.setStyleSheet("font-size: 14px; color: #7f8c8d; border: none;")
        self.lbl_elapsed.setVisible(False)
        status_layout.addWidget(self.lbl_elapsed)
        
        status_layout.addSpacing(10)
        
        btn_action_layout = QHBoxLayout()
        
        self.btn_start_session = QPushButton("Iniciar sesión")
        self.btn_start_session.setMinimumHeight(40)
        self.btn_start_session.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.btn_start_session.clicked.connect(self._start_session)
        
        self.btn_end_session = QPushButton("Finalizar sesión")
        self.btn_end_session.setMinimumHeight(40)
        self.btn_end_session.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.btn_end_session.clicked.connect(self._end_session)
        self.btn_end_session.setVisible(False)
        
        btn_action_layout.addWidget(self.btn_start_session)
        btn_action_layout.addWidget(self.btn_end_session)
        status_layout.addLayout(btn_action_layout)
        
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
        
        history_title = QLabel("Historial de Sesiones")
        history_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        history_layout.addWidget(history_title)
        
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background-color: transparent;")
        self.history_list_layout = QVBoxLayout(self.history_container)
        self.history_list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list_layout.setSpacing(10)
        self.history_list_layout.addStretch() # Mantener siempre al fondo
        
        self.history_scroll.setWidget(self.history_container)
        history_layout.addWidget(self.history_scroll)
        
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
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_lbl = QLabel(user.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        date_lbl = QLabel(f"Creado: {user.created_at}")
        date_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; border: none;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(date_lbl)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        btn_select = QPushButton("Seleccionar")
        btn_select.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        btn_select.clicked.connect(lambda _, u=user: self._select_user(u))
        layout.addWidget(btn_select)
        
        return widget

    def _show_create_user_dialog(self):
        from presentation.user_dialog import CreateUserDialog
        if not self.user_service:
            return
            
        dialog = CreateUserDialog(self.user_service, self)
        if dialog.exec():
            self._load_users()

    def _select_user(self, user):
        if self.user_service:
            self.user_service.set_active_user(user)
            self._update_active_user_display()

    def _update_active_user_display(self):
        if not self.user_service:
            return
        
        active_user = self.user_service.get_active_user()
        if active_user:
            self.lbl_active_user.setText(f"Usuario activo: {active_user.name}")
            self.lbl_active_user.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60; border: none;")
        else:
            self.lbl_active_user.setText("No hay usuario activo")
            self.lbl_active_user.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c; border: none;")
            
        self._update_session_ui_state()
        self._load_history()

    def _load_history(self):
        while self.history_list_layout.count() > 1:
            item = self.history_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        active_user = self.user_service.get_active_user() if self.user_service else None
        
        if not active_user or not self.session_service:
            self._show_empty_history_message("No hay usuario activo.")
            return
            
        try:
            sessions = self.session_service.get_user_sessions(active_user.id)
            if not sessions:
                self._show_empty_history_message("No hay sesiones registradas.")
            else:
                for session in sessions:
                    session_widget = self._create_session_widget(session)
                    self.history_list_layout.insertWidget(self.history_list_layout.count() - 1, session_widget)
        except Exception as e:
            self._show_empty_history_message()

    def _show_empty_history_message(self, message="No hay sesiones registradas."):
        empty_lbl = QLabel(message)
        empty_lbl.setStyleSheet("color: #95a5a6; font-style: italic; border: none; padding: 10px;")
        empty_lbl.setAlignment(Qt.AlignCenter)
        self.history_list_layout.insertWidget(0, empty_lbl)

    def _create_session_widget(self, session):
        widget = QFrame()
        widget.setStyleSheet("background-color: white; border-radius: 4px; padding: 10px; border: 1px solid #dcdde1;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Fecha
        date_str = session.started_at.strftime('%d/%m/%Y') if session.started_at else 'Desconocida'
        date_lbl = QLabel(f"Fecha: {date_str}")
        date_lbl.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        # Horas
        start_str = session.started_at.strftime('%H:%M:%S') if session.started_at else '...'
        end_str = session.ended_at.strftime('%H:%M:%S') if session.ended_at else 'En progreso'
        time_lbl = QLabel(f"Horario: {start_str} - {end_str}")
        time_lbl.setStyleSheet("color: #34495e; font-size: 13px; border: none;")
        
        # Duración
        duration_lbl = QLabel("Duración: ---")
        if session.duration_seconds is not None:
            hours, remainder = divmod(session.duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_lbl.setText(f"Duración: {hours:02d}:{minutes:02d}:{seconds:02d}")
        duration_lbl.setStyleSheet("color: #7f8c8d; font-size: 13px; border: none;")
        
        layout.addWidget(date_lbl)
        layout.addWidget(time_lbl)
        layout.addWidget(duration_lbl)
        return widget

    def _start_session(self):
        if not self.session_service:
            return
        try:
            self.session_service.start_session()
            self.timer.start(1000)
            self._update_session_ui_state()
        except Exception as e:
            QMessageBox.warning(self, "Error al iniciar", str(e))

    def _end_session(self):
        if not self.session_service:
            return
        try:
            self.session_service.end_session()
            self.timer.stop()
            self._update_session_ui_state()
            self._load_history()
        except Exception as e:
            QMessageBox.warning(self, "Error al finalizar", str(e))
            
    def _update_session_ui_state(self):
        active_session = self.session_service.get_active_session() if self.session_service else None
        active_user = self.user_service.get_active_user() if self.user_service else None
        
        if active_session:
            self.btn_start_session.setVisible(False)
            self.btn_end_session.setVisible(True)
            start_str = active_session.started_at.strftime('%H:%M:%S') if active_session.started_at else '...'
            self.lbl_status.setText(f"Sesión iniciada a las {start_str}")
            self.lbl_status.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold; border: none;")
            self.lbl_elapsed.setVisible(True)
        else:
            self.btn_start_session.setVisible(True)
            self.btn_end_session.setVisible(False)
            self.btn_start_session.setEnabled(active_user is not None)
            self.lbl_status.setText("Inactivo")
            self.lbl_status.setStyleSheet("color: #7f8c8d; font-size: 16px; border: none;")
            self.lbl_elapsed.setText("Transcurrido: 00:00:00")
            self.lbl_elapsed.setVisible(False)

    def _update_session_time(self):
        if not self.session_service: return
        session = self.session_service.get_active_session()
        if session and session.started_at:
            elapsed = datetime.now() - session.started_at
            total_seconds = int(elapsed.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_elapsed.setText(f"Transcurrido: {hours:02d}:{minutes:02d}:{seconds:02d}")
