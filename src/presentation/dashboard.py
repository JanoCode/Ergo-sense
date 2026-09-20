from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QScrollArea, QMessageBox
from PySide6.QtCore import Qt, QTimer
from datetime import datetime
import time
from domain.blink_detector import BlinkDetector
from domain.ear_calculator import get_eye_state
from domain.perclos_calculator import PerclosCalculator, ProlongedClosureDetector
from domain.metrics import EyeState

class DashboardWidget(QWidget):
    def __init__(self, user_service=None, session_service=None, camera_service=None, face_analyzer=None):
        super().__init__()
        self.user_service = user_service
        self.session_service = session_service
        self.camera_service = camera_service
        self.face_analyzer = face_analyzer
        self.blink_detector = BlinkDetector()
        self.perclos_calc = PerclosCalculator()
        self.prolonged_detector = ProlongedClosureDetector()
        self._last_frame_time: float = 0.0
        self._last_state = EyeState.UNKNOWN
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_session_time)
        
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self._update_frame)
        
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
        
        self.lbl_video = QLabel("Cámara inactiva")
        self.lbl_video.setStyleSheet("background-color: #ecf0f1; border-radius: 8px; color: #7f8c8d; font-weight: bold;")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setMinimumSize(320, 240)
        self.lbl_video.setVisible(False)
        status_layout.addWidget(self.lbl_video)
        
        self.metrics_container = QWidget()
        metrics_layout = QVBoxLayout(self.metrics_container)
        metrics_layout.setContentsMargins(0, 5, 0, 0)
        
        self.lbl_face_status = QLabel("Rostro no detectado")
        self.lbl_face_status.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px; border: none;")
        self.lbl_face_status.setAlignment(Qt.AlignCenter)
        metrics_layout.addWidget(self.lbl_face_status)
        
        self.lbl_ear = QLabel("EAR: ---")
        self.lbl_ear.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_ear)
        
        self.lbl_eye_state = QLabel("Estado: UNKNOWN")
        self.lbl_eye_state.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_eye_state)
        
        self.lbl_blinks = QLabel("Parpadeos: 0")
        self.lbl_blinks.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_blinks)
        
        self.lbl_bpm = QLabel("BPM: 0.0")
        self.lbl_bpm.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_bpm)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #dcdde1;")
        metrics_layout.addWidget(separator)
        
        self.lbl_perclos_60s = QLabel("PERCLOS 1min: ---")
        self.lbl_perclos_60s.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_perclos_60s)
        
        self.lbl_perclos_5min = QLabel("PERCLOS 5min: ---")
        self.lbl_perclos_5min.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_perclos_5min)
        
        self.lbl_prolonged_count = QLabel("Cierres prolongados: 0")
        self.lbl_prolonged_count.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_prolonged_count)
        
        self.lbl_closure_duration = QLabel("Cierre actual: 0.0s")
        self.lbl_closure_duration.setStyleSheet("color: #2c3e50; font-size: 13px; border: none;")
        metrics_layout.addWidget(self.lbl_closure_duration)
        
        self.metrics_container.setVisible(False)
        status_layout.addWidget(self.metrics_container)
        
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
            self.blink_detector.reset()
            self.perclos_calc.reset()
            self.prolonged_detector.reset()
            self._last_frame_time = 0.0
            self._last_state = EyeState.UNKNOWN
            self.timer.start(1000)
            
            if self.camera_service:
                if self.camera_service.start():
                    self.lbl_video.setVisible(True)
                    self.metrics_container.setVisible(True)
                    self.camera_timer.start(33) # ~30 fps
                else:
                    QMessageBox.warning(self, "Cámara no disponible", "No se pudo iniciar la cámara. La sesión continuará sin video.")
                    
            self._update_session_ui_state()
        except Exception as e:
            QMessageBox.warning(self, "Error al iniciar", str(e))

    def _end_session(self):
        if not self.session_service:
            return
        try:
            self.session_service.end_session()
            self.timer.stop()
            
            if self.camera_service:
                self.camera_service.stop()
                self.camera_timer.stop()
                self.lbl_video.setVisible(False)
                self.lbl_video.setText("Cámara inactiva")
                self.metrics_container.setVisible(False)
                
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

    def _update_frame(self):
        if not self.camera_service or not self.camera_service.is_running():
            return
            
        frame_rgb = self.camera_service.get_frame()
        if frame_rgb is not None:
            if self.face_analyzer:
                result = self.face_analyzer.analyze_frame(frame_rgb)
                current_time = time.time()
                
                if result:
                    self.lbl_face_status.setText("Rostro detectado")
                    self.lbl_face_status.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 13px; border: none;")
                    frame_rgb = self.face_analyzer.draw_landmarks(frame_rgb, result)
                    eye_metrics = get_eye_state(result)
                else:
                    self.lbl_face_status.setText("Rostro no detectado")
                    self.lbl_face_status.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px; border: none;")
                    eye_metrics = get_eye_state(None)
                    
                self.lbl_ear.setText(f"EAR: {eye_metrics.ear_avg:.3f}" if eye_metrics.ear_avg is not None else "EAR: ---")
                self.lbl_eye_state.setText(f"Estado: {eye_metrics.state.value}")
                
                self.blink_detector.process_state(eye_metrics.state, current_time)
                blink_metrics = self.blink_detector.get_metrics(current_time)
                
                self.lbl_blinks.setText(f"Parpadeos: {blink_metrics.total_blinks}")
                self.lbl_bpm.setText(f"BPM: {blink_metrics.blinks_per_minute:.1f}")
                
                # Alimentar PERCLOS y cierre prolongado con duración del intervalo
                if self._last_frame_time > 0 and eye_metrics.state != EyeState.UNKNOWN:
                    interval = current_time - self._last_frame_time
                    self.perclos_calc.add_event(current_time, eye_metrics.state, interval)
                    
                self._last_frame_time = current_time
                self._last_state = eye_metrics.state
                self.prolonged_detector.process_state(eye_metrics.state, current_time)
                
                # Actualizar labels de PERCLOS
                perclos = self.perclos_calc.get_perclos(current_time)
                self.lbl_perclos_60s.setText(
                    f"PERCLOS 1min: {perclos.perclos_60s*100:.1f}%" if perclos.perclos_60s is not None else "PERCLOS 1min: ---"
                )
                self.lbl_perclos_5min.setText(
                    f"PERCLOS 5min: {perclos.perclos_5min*100:.1f}%" if perclos.perclos_5min is not None else "PERCLOS 5min: ---"
                )
                
                # Actualizar cierres prolongados
                closure_result = self.prolonged_detector.get_result(current_time)
                self.lbl_prolonged_count.setText(f"Cierres prolongados: {closure_result.count}")
                self.lbl_closure_duration.setText(f"Cierre actual: {closure_result.current_duration:.1f}s")
                    
            from PySide6.QtGui import QImage, QPixmap
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
