from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.dashboard import DashboardWidget


class ModernDashboardWidget(DashboardWidget):
    """Presentation-only redesign built on the existing dashboard behavior."""

    PAGE_HOME = 0
    PAGE_MONITORING = 1
    PAGE_HISTORY = 2
    PAGE_TRENDS = 3
    PAGE_USERS = 4

    def _setup_ui(self):
        self.setStyleSheet(self._theme())
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_navigation())
        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.pages, 1)

        self.pages.addWidget(self._scroll_page(self._build_home()))
        self.pages.addWidget(self._scroll_page(self._build_monitoring()))
        self.pages.addWidget(self._scroll_page(self._build_history()))
        self.pages.addWidget(self._scroll_page(self._build_trends()))
        self.pages.addWidget(self._scroll_page(self._build_users()))
        self._navigate(self.PAGE_HOME)

    def _build_navigation(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(8)

        brand = QLabel("ErgoSense")
        brand.setObjectName("brand")
        tagline = QLabel("Bienestar durante tu jornada")
        tagline.setObjectName("sidebarCaption")
        tagline.setWordWrap(True)
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(24)

        self.nav_buttons = []
        for index, label in enumerate(
            ("Inicio", "Monitoreo", "Historial", "Tendencias", "Usuarios")
        ):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setMinimumHeight(42)
            button.clicked.connect(lambda _, value=index: self._navigate(value))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()

        self.lbl_active_user = QLabel("No hay usuario activo")
        self.lbl_active_user.setObjectName("sidebarUser")
        self.lbl_active_user.setWordWrap(True)
        layout.addWidget(self.lbl_active_user)
        return sidebar

    def _build_home(self):
        page, layout = self._page("Inicio", "Tu estado de un vistazo")

        self.home_empty = self._empty_state(
            "Selecciona o crea un usuario para comenzar",
            "Tus sesiones y resultados se guardarán de forma independiente.",
        )
        go_users = QPushButton("Ir a usuarios")
        go_users.setObjectName("primaryButton")
        go_users.clicked.connect(lambda: self._navigate(self.PAGE_USERS))
        self.home_empty.layout().addWidget(go_users, alignment=Qt.AlignCenter)
        layout.addWidget(self.home_empty)

        self.home_content = QWidget()
        content = QVBoxLayout(self.home_content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(16)

        welcome = self._card()
        self.home_welcome_card = welcome
        welcome_layout = QVBoxLayout(welcome)
        self.lbl_home_user = QLabel("Hola")
        self.lbl_home_user.setObjectName("sectionTitle")
        self.lbl_status = QLabel("Sin sesión")
        self.lbl_status.setObjectName("statusText")
        self.lbl_baseline_status = QLabel("Baseline no iniciado")
        self.lbl_baseline_status.setObjectName("mutedText")
        self.lbl_session_count = QLabel("Sesiones registradas: 0")
        self.lbl_session_count.setObjectName("mutedText")
        welcome_layout.addWidget(self.lbl_home_user)
        welcome_layout.addWidget(self.lbl_status)
        welcome_layout.addWidget(self.lbl_baseline_status)
        welcome_layout.addWidget(self.lbl_session_count)

        fatigue = self._card()
        self.home_fatigue_card = fatigue
        fatigue_layout = QVBoxLayout(fatigue)
        fatigue_title = QLabel("Fatiga actual")
        fatigue_title.setObjectName("eyebrow")
        self.lbl_home_score = QLabel("---")
        self.lbl_home_score.setObjectName("heroScore")
        self.home_score_bar = QProgressBar()
        self.home_score_bar.setRange(0, 100)
        self.home_score_bar.setValue(0)
        self.home_score_bar.setTextVisible(False)
        self.lbl_home_level = QLabel("Nivel: sin evaluación")
        self.lbl_home_level.setObjectName("sectionTitle")
        fatigue_layout.addWidget(fatigue_title)
        fatigue_layout.addWidget(self.lbl_home_score)
        fatigue_layout.addWidget(self.home_score_bar)
        fatigue_layout.addWidget(self.lbl_home_level)

        cards = QGridLayout()
        self.home_cards_layout = cards
        cards.setSpacing(16)
        cards.addWidget(welcome, 0, 0)
        cards.addWidget(fatigue, 0, 1)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)
        content.addLayout(cards)

        self.lbl_elapsed = QLabel("Transcurrido: 00:00:00")
        self.lbl_elapsed.setObjectName("sessionTime")
        self.lbl_elapsed.setAlignment(Qt.AlignCenter)
        content.addWidget(self.lbl_elapsed)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_start_session = QPushButton("Iniciar monitoreo")
        self.btn_start_session.setObjectName("primaryButton")
        self.btn_start_session.setMinimumHeight(48)
        self.btn_start_session.clicked.connect(self._start_session)
        self.btn_end_session = QPushButton("Finalizar monitoreo")
        self.btn_end_session.setObjectName("dangerButton")
        self.btn_end_session.setMinimumHeight(48)
        self.btn_end_session.clicked.connect(lambda: self._end_session())
        actions.addWidget(self.btn_start_session)
        actions.addWidget(self.btn_end_session)
        actions.addStretch()
        content.addLayout(actions)
        layout.addWidget(self.home_content)
        layout.addStretch()
        return page

    def _build_monitoring(self):
        page, layout = self._page(
            "Monitoreo", "Seguimiento en tiempo real durante la sesión"
        )
        self.monitoring_empty = self._empty_state(
            "No hay una sesión activa",
            "Inicia el monitoreo desde Inicio cuando estés listo.",
        )
        go_home = QPushButton("Volver a Inicio")
        go_home.setObjectName("secondaryButton")
        go_home.clicked.connect(lambda: self._navigate(self.PAGE_HOME))
        self.monitoring_empty.layout().addWidget(go_home, alignment=Qt.AlignCenter)
        layout.addWidget(self.monitoring_empty)

        self.monitoring_content = QWidget()
        monitor_layout = QVBoxLayout(self.monitoring_content)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.setSpacing(16)
        upper = QHBoxLayout()
        upper.setSpacing(16)

        video_card = self._card()
        self.monitor_video_card = video_card
        video_layout = QVBoxLayout(video_card)
        self.lbl_video = QLabel("Cámara inactiva")
        self.lbl_video.setObjectName("videoSurface")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setMinimumSize(320, 240)
        self.lbl_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_camera_status = QLabel("Iniciando cámara...")
        self.lbl_camera_status.setObjectName("cameraStatus")
        self.lbl_camera_status.setAlignment(Qt.AlignCenter)
        self.lbl_face_status = QLabel("Rostro no detectado")
        self.lbl_face_status.setObjectName("stateBadge")
        self.lbl_face_status.setAlignment(Qt.AlignCenter)
        self.btn_retry_camera = QPushButton("Reintentar cámara")
        self.btn_retry_camera.setObjectName("secondaryButton")
        self.btn_retry_camera.clicked.connect(self._retry_monitoring)
        self.btn_retry_camera.setVisible(False)
        video_layout.addWidget(self.lbl_video, 1)
        video_layout.addWidget(self.lbl_camera_status)
        video_layout.addWidget(self.lbl_face_status)
        video_layout.addWidget(self.btn_retry_camera, alignment=Qt.AlignCenter)
        upper.addWidget(video_card, 3)

        score_card = self._card()
        self.monitor_score_card = score_card
        score_layout = QVBoxLayout(score_card)
        score_layout.setAlignment(Qt.AlignTop)
        title = QLabel("Fatiga actual")
        title.setObjectName("eyebrow")
        self.lbl_fatigue_score = QLabel("--- / 100")
        self.lbl_fatigue_score.setObjectName("monitorScore")
        self.lbl_fatigue_level = QLabel("Nivel: sin evaluación")
        self.lbl_fatigue_level.setObjectName("stateBadge")
        self.lbl_fatigue_confidence = QLabel("Confianza: ---")
        self.lbl_fatigue_confidence.setObjectName("mutedText")
        self.lbl_monitor_time = QLabel("00:00:00")
        self.lbl_monitor_time.setObjectName("sessionTime")
        self.btn_monitor_end = QPushButton("Finalizar monitoreo")
        self.btn_monitor_end.setObjectName("dangerButton")
        self.btn_monitor_end.clicked.connect(lambda: self._end_session())
        for widget in (
            title, self.lbl_fatigue_score, self.lbl_fatigue_level,
            self.lbl_fatigue_confidence, self.lbl_monitor_time,
            self.btn_monitor_end,
        ):
            score_layout.addWidget(widget)
        self.lbl_current_state = QLabel("Estado actual · esperando evaluación")
        self.lbl_current_state.setWordWrap(True)
        self.lbl_current_state.setObjectName("stateBadge")
        self.monitor_score_bar = QProgressBar()
        self.monitor_score_bar.setRange(0, 100)
        self.monitor_score_bar.setTextVisible(False)
        self.lbl_recommendation = QLabel("La primera evaluación necesita una ventana de observación.")
        self.lbl_recommendation.setWordWrap(True)
        self.lbl_reasons = QLabel("¿Qué está detectando?\nEsperando datos suficientes.")
        self.lbl_reasons.setWordWrap(True)
        for widget in (self.lbl_current_state, self.monitor_score_bar,
                       self.lbl_recommendation, self.lbl_reasons):
            score_layout.addWidget(widget)
        upper.addWidget(score_card, 1)
        self.monitor_upper_layout = upper
        monitor_layout.addLayout(upper, 1)

        summary = QGridLayout()
        self.monitor_summary_layout = summary
        summary.setSpacing(12)
        self.lbl_perclos_60s = self._metric("Cierre ocular (PERCLOS)", "---")
        self.lbl_perclos_60s.setToolTip(
            "Porcentaje de tiempo con los ojos cerrados durante el último minuto."
        )
        self.lbl_bpm = self._metric("Parpadeos por minuto", "---")
        self.lbl_yawns = self._metric("Bostezos", "0")
        self.lbl_yawns.setInterpretation("Aperturas sostenidas detectadas")
        self.lbl_head_dev = self._metric("Postura", "Esperando detección facial")
        for column, widget in enumerate(
            (self.lbl_perclos_60s, self.lbl_bpm, self.lbl_yawns, self.lbl_head_dev)
        ):
            summary.addWidget(widget, 0, column)
            summary.setColumnStretch(column, 1)
        monitor_layout.addLayout(summary)
        self.lbl_metric_context = QLabel("Esperando detección facial")
        self.lbl_metric_context.setWordWrap(True)
        monitor_layout.addWidget(self.lbl_metric_context)
        self.landmarks_toggle = QCheckBox("Mostrar puntos de detección")
        self.landmarks_toggle.toggled.connect(self._set_landmarks_visible)
        monitor_layout.addWidget(self.landmarks_toggle)
        self.lbl_yawn_feedback = QLabel("")
        monitor_layout.addWidget(self.lbl_yawn_feedback)
        from PySide6.QtCore import QTimer
        self.yawn_feedback_timer = QTimer(self)
        self.yawn_feedback_timer.setSingleShot(True)
        self.yawn_feedback_timer.timeout.connect(self.lbl_yawn_feedback.clear)
        self._displayed_yawns = 0

        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("Ver métricas avanzadas")
        self.advanced_toggle.setObjectName("advancedButton")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        monitor_layout.addWidget(self.advanced_toggle, alignment=Qt.AlignLeft)

        self.metrics_container = self._card()
        advanced = QGridLayout(self.metrics_container)
        self.lbl_ear = self._plain_metric("EAR: ---", "Apertura ocular estimada.")
        self.lbl_eye_state = self._plain_metric("Estado ocular: UNKNOWN")
        self.lbl_blinks = self._plain_metric("Parpadeos: 0")
        self.lbl_perclos_5min = self._plain_metric("PERCLOS 5 min: ---")
        self.lbl_prolonged_count = self._plain_metric("Cierres prolongados: 0")
        self.lbl_closure_duration = self._plain_metric("Cierre actual: 0.0 s")
        self.lbl_mar = self._plain_metric("MAR: ---", "Apertura de la boca estimada.")
        self.lbl_pitch = self._plain_metric("Pitch: ---")
        self.lbl_yaw = self._plain_metric("Yaw: ---")
        self.lbl_roll = self._plain_metric("Roll: ---")
        self.lbl_fatigue_signals = self._plain_metric("Razones principales: ---")
        self.lbl_fatigue_signals.setWordWrap(True)
        advanced_widgets = (
            self.lbl_ear, self.lbl_eye_state, self.lbl_blinks,
            self.lbl_perclos_5min, self.lbl_prolonged_count,
            self.lbl_closure_duration, self.lbl_mar, self.lbl_pitch,
            self.lbl_yaw, self.lbl_roll, self.lbl_fatigue_signals,
        )
        for index, widget in enumerate(advanced_widgets):
            advanced.addWidget(widget, index // 3, index % 3)
        self.metrics_container.setVisible(False)
        monitor_layout.addWidget(self.metrics_container)
        layout.addWidget(self.monitoring_content)
        return page

    def _build_history(self):
        page, layout = self._page(
            "Historial", "Consulta y compara tus sesiones anteriores"
        )
        content = QHBoxLayout()
        content.setSpacing(16)
        self.history_container = QScrollArea()
        self.history_container.setWidgetResizable(True)
        history_list = QWidget()
        self.history_list_layout = QVBoxLayout(history_list)
        self.history_list_layout.setAlignment(Qt.AlignTop)
        self.history_list_layout.addStretch()
        self.history_container.setWidget(history_list)
        self.history_content_layout = content
        content.addWidget(self.history_container, 1)

        detail = self._card()
        self.history_detail_card = detail
        detail_layout = QVBoxLayout(detail)
        detail_title = QLabel("Detalle de sesión")
        detail_title.setObjectName("sectionTitle")
        self.lbl_session_detail = QLabel(
            "Selecciona una sesión para consultar sus métricas."
        )
        self.lbl_session_detail.setWordWrap(True)
        self.lbl_session_detail.setAlignment(Qt.AlignTop)
        detail_layout.addWidget(detail_title)
        detail_layout.addWidget(self.lbl_session_detail)
        detail_layout.addStretch()
        content.addWidget(detail, 2)
        layout.addLayout(content)
        return page

    def _build_trends(self):
        page, layout = self._page(
            "Tendencias", "Evolución basada exclusivamente en sesiones guardadas"
        )
        overview = QGridLayout()
        self.trends_overview_layout = overview
        overview.setSpacing(12)
        self.lbl_analytics_score = self._metric("Promedio últimos 7 días", "---")
        self.lbl_analytics_score_30 = self._metric("Promedio últimos 30 días", "---")
        self.lbl_analytics_moderate = self._metric("Tiempo hasta fatiga moderada", "---")
        self.lbl_analytics_trend = self._metric("Tendencia", "Sin datos suficientes")
        self.lbl_analytics_comparison = self._plain_metric("Comparación: ---")
        self.lbl_analytics_sessions = self._plain_metric("Sesiones analizadas: 0")
        for index, widget in enumerate(
            (
                self.lbl_analytics_score, self.lbl_analytics_score_30,
                self.lbl_analytics_moderate, self.lbl_analytics_trend,
            )
        ):
            overview.addWidget(widget, index // 2, index % 2)
        layout.addLayout(overview)
        layout.addWidget(self.lbl_analytics_comparison)
        layout.addWidget(self.lbl_analytics_sessions)

        self.chart_score = self._create_chart_view()
        self.chart_moderate = self._create_chart_view()
        self.chart_perclos = self._create_chart_view()
        charts = QGridLayout()
        self.trends_charts_layout = charts
        charts.setSpacing(14)
        charts.addWidget(self.chart_score, 0, 0, 1, 2)
        charts.addWidget(self.chart_moderate, 1, 0)
        charts.addWidget(self.chart_perclos, 1, 1)
        layout.addLayout(charts)

        insights = self._card()
        insights_layout = QVBoxLayout(insights)
        insights_title = QLabel("Observaciones")
        insights_title.setObjectName("sectionTitle")
        self.lbl_longitudinal_insights = QLabel(
            "Aún no hay suficientes datos para generar observaciones."
        )
        self.lbl_longitudinal_insights.setWordWrap(True)
        insights_layout.addWidget(insights_title)
        insights_layout.addWidget(self.lbl_longitudinal_insights)
        layout.addWidget(insights)
        return page

    def _build_users(self):
        page, layout = self._page(
            "Usuarios", "Cada perfil mantiene su propio baseline e historial"
        )
        header = QHBoxLayout()
        active = QLabel("Selecciona el perfil que utilizará la aplicación")
        active.setObjectName("mutedText")
        self.btn_create_user = QPushButton("Crear usuario")
        self.btn_create_user.setObjectName("primaryButton")
        self.btn_create_user.clicked.connect(self._show_create_user_dialog)
        header.addWidget(active)
        header.addStretch()
        header.addWidget(self.btn_create_user)
        layout.addLayout(header)

        self.users_container = QScrollArea()
        self.users_container.setWidgetResizable(True)
        users_list = QWidget()
        self.users_list_layout = QVBoxLayout(users_list)
        self.users_list_layout.setAlignment(Qt.AlignTop)
        self.users_list_layout.addStretch()
        self.users_container.setWidget(users_list)
        layout.addWidget(self.users_container)
        return page

    def _navigate(self, index):
        if index == self.PAGE_USERS:
            self._load_users()
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _toggle_advanced(self, checked):
        self.metrics_container.setVisible(checked)
        self.advanced_toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.advanced_toggle.setText(
            "Ocultar métricas avanzadas" if checked else "Ver métricas avanzadas"
        )

    def _start_session(self):
        from ui.theme import style_level
        style_level(self.lbl_current_state)
        style_level(self.lbl_fatigue_level)
        for card in (self.lbl_perclos_60s, self.lbl_bpm, self.lbl_head_dev):
            card.setInterpretation("Esperando datos")
        self._displayed_yawns = 0
        self.lbl_yawn_feedback.clear()
        self.yawn_feedback_timer.stop()
        self.lbl_current_state.setText("Estado actual · esperando evaluación")
        self.lbl_recommendation.setText("La primera evaluación necesita una ventana de observación.")
        self.lbl_reasons.setText("¿Qué está detectando?\nEsperando datos suficientes.")
        self.monitor_score_bar.setValue(0)
        super()._start_session()
        if self.session_service and self.session_service.get_active_session():
            self.metrics_container.setVisible(self.advanced_toggle.isChecked())
            self._navigate(self.PAGE_MONITORING)

    def _end_session(self, show_summary=True):
        super()._end_session(show_summary)
        self._navigate(self.PAGE_HOME)

    def _update_session_ui_state(self):
        super()._update_session_ui_state()
        self.lbl_status.setStyleSheet("")
        active = bool(
            self.session_service and self.session_service.get_active_session()
        )
        has_user = bool(self.user_service and self.user_service.get_active_user())
        self.home_empty.setVisible(not has_user)
        self.home_content.setVisible(has_user)
        self.monitoring_empty.setVisible(not active)
        self.monitoring_content.setVisible(active)
        self.btn_monitor_end.setVisible(active)
        if active:
            baseline_state = (
                self.baseline_service.get_state() if self.baseline_service else None
            )
            if baseline_state and baseline_state.value != "READY":
                self.lbl_status.setText("Calibrando · monitoreo activo")
            else:
                self.lbl_status.setText("Monitoreando")
        else:
            self.lbl_status.setText("Sin sesión")

    def _update_active_user_display(self):
        super()._update_active_user_display()
        self.lbl_active_user.setStyleSheet("")
        user = self.user_service.get_active_user() if self.user_service else None
        self.lbl_home_user.setText(f"Hola, {user.name}" if user else "Hola")
        self._update_session_ui_state()

    def _update_baseline_label(self):
        super()._update_baseline_label()
        self.lbl_baseline_status.setStyleSheet("")

    def _create_user_widget(self, user):
        card = self._card()
        layout = QHBoxLayout(card)
        name = QLabel(user.name)
        name.setObjectName("sectionTitle")
        name.setWordWrap(True)
        details = QVBoxLayout()
        details.addWidget(name)
        if user.created_at:
            from datetime import datetime
            try:
                date_text = datetime.fromisoformat(user.created_at).strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                date_text = str(user.created_at)
            created = QLabel("Creado: " + date_text)
            created.setObjectName("mutedText")
            details.addWidget(created)
        layout.addLayout(details, 1)
        select = QPushButton("Seleccionar perfil")
        select.setObjectName("secondaryButton")
        select.clicked.connect(lambda: self._select_user(user))
        layout.addWidget(select)
        return card

    @staticmethod
    def _set_line_chart(view, title, points, y_title):
        from ui.theme import style_chart
        DashboardWidget._set_line_chart(view, title, points, y_title)
        style_chart(view.chart())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = event.size().width() < 1300
        if compact:
            self.home_cards_layout.addWidget(self.home_welcome_card, 0, 0)
            self.home_cards_layout.addWidget(self.home_fatigue_card, 1, 0)
            self.monitor_upper_layout.setDirection(QVBoxLayout.TopToBottom)
            for index, widget in enumerate(
                (
                    self.lbl_perclos_60s, self.lbl_bpm,
                    self.lbl_yawns, self.lbl_head_dev,
                )
            ):
                self.monitor_summary_layout.addWidget(
                    widget, index // 2, index % 2
                )
            self.history_content_layout.setDirection(QHBoxLayout.TopToBottom)
            for index, widget in enumerate(
                (
                    self.lbl_analytics_score,
                    self.lbl_analytics_score_30,
                    self.lbl_analytics_moderate,
                    self.lbl_analytics_trend,
                )
            ):
                self.trends_overview_layout.addWidget(widget, index, 0)
            self.trends_charts_layout.addWidget(self.chart_score, 0, 0)
            self.trends_charts_layout.addWidget(self.chart_moderate, 1, 0)
            self.trends_charts_layout.addWidget(self.chart_perclos, 2, 0)
        else:
            self.home_cards_layout.addWidget(self.home_welcome_card, 0, 0)
            self.home_cards_layout.addWidget(self.home_fatigue_card, 0, 1)
            self.monitor_upper_layout.setDirection(QHBoxLayout.LeftToRight)
            for index, widget in enumerate(
                (
                    self.lbl_perclos_60s, self.lbl_bpm,
                    self.lbl_yawns, self.lbl_head_dev,
                )
            ):
                self.monitor_summary_layout.addWidget(widget, 0, index)
            self.history_content_layout.setDirection(QHBoxLayout.LeftToRight)
            for index, widget in enumerate(
                (
                    self.lbl_analytics_score,
                    self.lbl_analytics_score_30,
                    self.lbl_analytics_moderate,
                    self.lbl_analytics_trend,
                )
            ):
                self.trends_overview_layout.addWidget(widget, index // 2, index % 2)
            self.trends_charts_layout.addWidget(self.chart_score, 0, 0, 1, 2)
            self.trends_charts_layout.addWidget(self.chart_moderate, 1, 0)
            self.trends_charts_layout.addWidget(self.chart_perclos, 1, 1)

    def _update_session_time(self):
        super()._update_session_time()
        value = self.lbl_elapsed.text().replace("Transcurrido: ", "")
        self.lbl_monitor_time.setText(value)

    def _reset_fatigue_ui(self):
        super()._reset_fatigue_ui()
        self._sync_score()

    def _update_fatigue_assessment(self, *args, **kwargs):
        super()._update_fatigue_assessment(*args, **kwargs)
        self._sync_score()
        assessment = getattr(self, "current_assessment", None)
        if assessment is not None:
            from ui.fatigue_feedback import level_feedback, readable_reasons
            title, recommendation, color = level_feedback(assessment.level)
            from ui.theme import style_level
            style_level(self.lbl_current_state, color)
            style_level(self.lbl_fatigue_level, color)
            self.lbl_current_state.setText("Estado actual\n" + title)
            self.lbl_recommendation.setText(recommendation)
            self.monitor_score_bar.setValue(round(assessment.score))
            self.monitor_score_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {color}; }}"
            )
            self.lbl_reasons.setText("¿Qué está detectando?\n" + readable_reasons(assessment.reasons))

    def _start_monitoring_worker(self):
        super()._start_monitoring_worker()
        self._set_landmarks_visible(self.landmarks_toggle.isChecked())

    def _set_landmarks_visible(self, enabled):
        worker = self.monitoring_worker
        if worker is not None:
            worker.show_landmarks.set() if enabled else worker.show_landmarks.clear()

    def _on_monitoring_sample(self, sample):
        super()._on_monitoring_sample(sample)
        self.lbl_face_status.setStyleSheet("")
        if not sample.analyzed:
            return
        count = sample.yawn_metrics.total_yawns
        if count > self._displayed_yawns:
            self.lbl_yawn_feedback.setText("Bostezo detectado")
            self.yawn_feedback_timer.start(3500)
        self._displayed_yawns = count
        if not sample.face_detected:
            self.lbl_metric_context.setText("Sin detección facial: interpretación no disponible.")
            for card in (self.lbl_perclos_60s, self.lbl_bpm, self.lbl_head_dev):
                card.setInterpretation("Sin detección facial")
            return
        from ui.fatigue_feedback import metric_context
        baseline = self.baseline_service.get_baseline() if self.baseline_service else None
        self.lbl_metric_context.setText(metric_context(sample, baseline, self.fatigue_engine.config))
        parts = self.lbl_metric_context.text().split(" · ")
        for card, interpretation in zip(
            (self.lbl_perclos_60s, self.lbl_bpm, self.lbl_head_dev), parts
        ):
            card.setInterpretation(interpretation.split(": ", 1)[-1])
        self.lbl_metric_context.hide()

    def _sync_score(self):
        text = self.lbl_fatigue_score.text()
        digits = "".join(char for char in text.split("/")[0] if char.isdigit())
        value = int(digits) if digits else 0
        if value < 20:
            color = "#238a5a"
        elif value < 40:
            color = "#b77900"
        elif value < 60:
            color = "#d96812"
        else:
            color = "#c93737"
        self.home_score_bar.setValue(max(0, min(value, 100)))
        self.home_score_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}"
        )
        self.lbl_home_score.setText(f"{value} / 100" if digits else "---")
        if digits:
            self.lbl_fatigue_score.setText(f"{value} / 100")
        level_text = self.lbl_fatigue_level.text()
        translations = {
            "VERY_HIGH": "Muy alta",
            "MODERATE": "Moderada",
            "NORMAL": "Normal",
            "MILD": "Leve",
            "HIGH": "Alta",
        }
        for source, target in translations.items():
            level_text = level_text.replace(source, target)
        self.lbl_fatigue_level.setText(level_text)
        self.lbl_home_level.setText(level_text)

    def _create_session_widget(self, session):
        widget = self._card()
        layout = QHBoxLayout(widget)
        text = QVBoxLayout()
        date = session.started_at.strftime("%d/%m/%Y · %H:%M") if session.started_at else "Fecha desconocida"
        title = QLabel(date)
        title.setObjectName("sectionTitle")
        duration = "En curso"
        if session.duration_seconds is not None:
            hours, remainder = divmod(session.duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        summary = (
            self.fatigue_history_service.get_summary(session.id)
            if self.fatigue_history_service and session.id is not None else None
        )
        score = f"{summary.average_score:.1f}" if summary and summary.average_score is not None else "---"
        level = summary.max_level.value if summary and summary.max_level else "---"
        subtitle = QLabel(
            f"Duración: {duration}   ·   Score promedio: {score}   ·   Nivel máximo: {level}"
        )
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(subtitle)
        layout.addLayout(text, 1)
        button = QPushButton("Ver detalle")
        button.setObjectName("secondaryButton")
        button.clicked.connect(lambda _, value=session: self._show_session_detail(value))
        layout.addWidget(button)
        return widget

    @staticmethod
    def _page(title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        caption = QLabel(subtitle)
        caption.setObjectName("pageSubtitle")
        caption.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(caption)
        return page, layout

    @staticmethod
    def _scroll_page(content):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return card

    def _metric(self, title, value):
        card = self._card()
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.setProperty("valueLabel", value_label)
        return _MetricCard(card, value_label)

    @staticmethod
    def _plain_metric(text, tooltip=""):
        label = QLabel(text)
        label.setObjectName("plainMetric")
        label.setToolTip(tooltip)
        return label

    @staticmethod
    def _empty_state(title, subtitle):
        frame = QFrame()
        frame.setObjectName("emptyState")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        heading.setAlignment(Qt.AlignCenter)
        heading.setWordWrap(True)
        caption = QLabel(subtitle)
        caption.setObjectName("mutedText")
        caption.setAlignment(Qt.AlignCenter)
        caption.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(caption)
        return frame

    @staticmethod
    def _create_chart_view():
        from ui.theme import style_chart
        view = DashboardWidget._create_chart_view()
        style_chart(view.chart())
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(210)
        return view

    @staticmethod
    def _theme():
        from ui.theme import QSS
        return QSS

class _MetricCard(QFrame):
    """Card-compatible label adapter used by existing presentation methods."""

    def __init__(self, card, value_label):
        super().__init__()
        self.setObjectName("card")
        self._value_label = value_label
        layout = card.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(self)
                QVBoxLayout(self) if self.layout() is None else None
                self.layout().addWidget(item.widget())
        self._value_label.setWordWrap(True)
        self._interpretation = QLabel("")
        self._interpretation.setObjectName("mutedText")
        self._interpretation.setWordWrap(True)
        self.layout().addWidget(self._interpretation)

    def setInterpretation(self, text):
        self._interpretation.setText(text)

    def setText(self, text):
        value = text.split(":", 1)[-1].strip() if ":" in text else text
        self._value_label.setText(value)

    def text(self):
        return self._value_label.text()
