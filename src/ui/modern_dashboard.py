from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from ui.dashboard import DashboardWidget


class ModernDashboardWidget(DashboardWidget):
    PAGE_HOME = 0
    PAGE_WELLBEING = 1
    PAGE_HISTORY = 2
    PAGE_SETTINGS = 3
    PAGE_USERS = 4

    def _setup_ui(self):
        self.setStyleSheet(self._theme())
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_navigation())
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.pages.addWidget(self._scroll_page(self._build_home()))
        self.pages.addWidget(self._scroll_page(self._build_wellbeing()))
        self.pages.addWidget(self._scroll_page(self._build_history()))
        self.pages.addWidget(self._scroll_page(self._build_settings()))
        self.pages.addWidget(self._scroll_page(self._build_users()))
        self._navigate(self.PAGE_HOME)

    def _build_navigation(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        brand = QLabel("ErgoSense")
        brand.setObjectName("brand")
        tagline = QLabel("Bienestar durante tu jornada")
        tagline.setObjectName("sidebarCaption")
        tagline.setWordWrap(True)
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(24)
        self.nav_buttons = []
        for index, text in enumerate(
            ("Inicio", "Bienestar", "Historial", "Configuración", "Usuarios")
        ):
            button = QPushButton(text)
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
            "Selecciona o crea un usuario para comenzar.",
            "Tus sesiones y pausas se guardarán en su perfil.",
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
        cards = QGridLayout()
        self.home_cards_layout = cards
        self.home_welcome_card = self._card()
        welcome = QVBoxLayout(self.home_welcome_card)
        self.lbl_home_user = QLabel("Hola")
        self.lbl_home_user.setObjectName("sectionTitle")
        self.lbl_status = QLabel("Sin sesión")
        self.lbl_status.setObjectName("statusText")
        self.lbl_session_count = QLabel("Sesiones registradas: 0")
        self.lbl_session_count.setObjectName("mutedText")
        welcome.addWidget(self.lbl_home_user)
        welcome.addWidget(self.lbl_status)
        welcome.addWidget(self.lbl_session_count)
        self.home_state_card = self._card()
        state_layout = QVBoxLayout(self.home_state_card)
        state_title = QLabel("Estado de descanso")
        state_title.setObjectName("eyebrow")
        self.lbl_home_level = QLabel("Sin sesión activa")
        self.lbl_home_level.setObjectName("sectionTitle")
        state_layout.addWidget(state_title)
        state_layout.addWidget(self.lbl_home_level)
        cards.addWidget(self.home_welcome_card, 0, 0)
        cards.addWidget(self.home_state_card, 0, 1)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)
        content.addLayout(cards)
        self.lbl_elapsed = self._centered("Tiempo de sesión: 00:00:00")
        self.lbl_continuous_usage = self._centered("Uso continuo: 00:00:00")
        self.lbl_break_info = self._centered("Próxima pausa en: -- min")
        content.addWidget(self.lbl_elapsed)
        content.addWidget(self.lbl_continuous_usage)
        content.addWidget(self.lbl_break_info)
        self._build_break_cards(content)
        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_start_session = QPushButton("Iniciar sesión")
        self.btn_start_session.setObjectName("primaryButton")
        self.btn_start_session.clicked.connect(self._start_session)
        self.btn_end_session = QPushButton("Finalizar sesión")
        self.btn_end_session.setObjectName("dangerButton")
        self.btn_end_session.clicked.connect(self._end_session)
        actions.addWidget(self.btn_start_session)
        actions.addWidget(self.btn_end_session)
        actions.addStretch()
        content.addLayout(actions)
        layout.addWidget(self.home_content)
        return page

    def _build_break_cards(self, content):
        self.break_reminder_card = self._card()
        reminder = QVBoxLayout(self.break_reminder_card)
        self.lbl_reminder_title = QLabel("Es un buen momento para hacer una pausa")
        self.lbl_reminder_title.setObjectName("sectionTitle")
        self.lbl_reminder_body = QLabel("")
        self.lbl_reminder_tip = QLabel("")
        for label in (self.lbl_reminder_title, self.lbl_reminder_body,
                      self.lbl_reminder_tip):
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            reminder.addWidget(label)
        row = QHBoxLayout()
        row.addStretch()
        self.btn_start_break = QPushButton("Iniciar pausa")
        self.btn_start_break.setObjectName("primaryButton")
        self.btn_start_break.clicked.connect(self._on_start_break)
        self.btn_postpone = QPushButton("Recordarme después")
        self.btn_postpone.setObjectName("secondaryButton")
        self.btn_postpone.clicked.connect(self._on_postpone)
        row.addWidget(self.btn_start_break)
        row.addWidget(self.btn_postpone)
        row.addStretch()
        reminder.addLayout(row)
        self.break_reminder_card.hide()
        content.addWidget(self.break_reminder_card)

        self.breaking_card = self._card()
        breaking = QVBoxLayout(self.breaking_card)
        self.lbl_breaking_title = QLabel("Pausa en curso")
        self.lbl_breaking_title.setObjectName("sectionTitle")
        self.lbl_breaking_since = QLabel("")
        self.lbl_break_timer = QLabel("")
        self.lbl_break_timer.setObjectName("sessionTime")
        self.lbl_break_suggestions_title = QLabel("Sugerencias para esta pausa")
        self.lbl_break_suggestions_title.setObjectName("eyebrow")
        self.lbl_break_suggestions = QLabel("")
        for label in (
            self.lbl_breaking_title, self.lbl_breaking_since,
            self.lbl_break_timer, self.lbl_break_suggestions_title,
            self.lbl_break_suggestions,
        ):
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            breaking.addWidget(label)
        self.btn_finish_break = QPushButton("Finalizar pausa")
        self.btn_finish_break.setObjectName("secondaryButton")
        self.btn_finish_break.clicked.connect(self._on_finish_break)
        breaking.addWidget(self.btn_finish_break, alignment=Qt.AlignCenter)
        self.breaking_card.hide()
        content.addWidget(self.breaking_card)
        self.lbl_break_completed = self._centered("Pausa completada")
        self.lbl_break_completed.hide()
        content.addWidget(self.lbl_break_completed)

    def _build_wellbeing(self):
        page, layout = self._page(
            "Bienestar", "Tu ciclo de trabajo y pausas durante la sesión"
        )
        self.wellbeing_empty = self._empty_state(
            "Inicia una sesión para comenzar a registrar tu tiempo de uso.",
            "Desde Inicio puedes comenzar cuando estés listo.",
        )
        layout.addWidget(self.wellbeing_empty)
        self.wellbeing_content = self._card()
        content = QVBoxLayout(self.wellbeing_content)
        self.lbl_wellbeing_state = QLabel("En buen ritmo")
        self.lbl_wellbeing_state.setObjectName("sectionTitle")
        self.lbl_monitor_time = self._centered("Tiempo de sesión: 00:00:00")
        self.lbl_monitor_continuous = self._centered("Uso continuo: 00:00:00")
        self.lbl_monitor_next_break = QLabel("Próxima pausa en: -- min")
        self.lbl_monitor_breaks = QLabel("Aún no has realizado pausas en esta sesión.")
        for widget in (
            self.lbl_wellbeing_state, self.lbl_monitor_time,
            self.lbl_monitor_continuous, self.lbl_monitor_next_break,
            self.lbl_monitor_breaks,
        ):
            content.addWidget(widget)
        self.btn_monitor_end = QPushButton("Finalizar sesión")
        self.btn_monitor_end.setObjectName("dangerButton")
        self.btn_monitor_end.clicked.connect(self._end_session)
        content.addWidget(self.btn_monitor_end, alignment=Qt.AlignLeft)
        layout.addWidget(self.wellbeing_content)
        return page

    def _build_history(self):
        page, layout = self._page("Historial", "Revisa tus sesiones y hábitos de descanso")
        overview = QGridLayout()
        self.lbl_week_sessions = self._metric("Sesiones últimos 7 días", "0")
        self.lbl_week_usage = self._metric("Tiempo total de uso", "00:00:00")
        self.lbl_week_breaks = self._metric("Pausas realizadas", "0")
        self.lbl_week_continuous = self._metric("Promedio antes de una pausa", "Sin datos")
        for index, card in enumerate((self.lbl_week_sessions, self.lbl_week_usage,
                                      self.lbl_week_breaks, self.lbl_week_continuous)):
            overview.addWidget(card, index // 2, index % 2)
        layout.addLayout(overview)
        self.lbl_period_summary = QLabel("Selecciona un usuario para consultar sus estadísticas.")
        self.lbl_period_summary.setWordWrap(True)
        self.lbl_period_summary.setObjectName("mutedText")
        layout.addWidget(self.lbl_period_summary)
        self.history_content_layout = QHBoxLayout()
        self.history_container = QScrollArea()
        self.history_container.setWidgetResizable(True)
        history_list = QWidget()
        self.history_list_layout = QVBoxLayout(history_list)
        self.history_list_layout.addStretch()
        self.history_container.setWidget(history_list)
        self.history_content_layout.addWidget(self.history_container, 1)
        detail = self._card()
        detail_layout = QVBoxLayout(detail)
        title = QLabel("Detalle de sesión")
        title.setObjectName("sectionTitle")
        self.lbl_session_detail = QLabel("Selecciona una sesión para consultar sus pausas y tiempos.")
        self.lbl_session_detail.setWordWrap(True)
        detail_layout.addWidget(title)
        detail_layout.addWidget(self.lbl_session_detail)
        detail_layout.addStretch()
        self.history_content_layout.addWidget(detail, 2)
        layout.addLayout(self.history_content_layout)
        self.history_charts_layout = QGridLayout()
        self.chart_daily_usage = self._create_chart_view()
        self.chart_daily_breaks = self._create_chart_view()
        self.history_charts_layout.addWidget(self.chart_daily_usage, 0, 0)
        self.history_charts_layout.addWidget(self.chart_daily_breaks, 0, 1)
        layout.addLayout(self.history_charts_layout)
        return page

    def _build_settings(self):
        from app import config
        page, layout = self._page("Configuración", "Intervalos del ciclo de trabajo y pausas")
        card = self._card()
        content = QVBoxLayout(card)
        title = QLabel("Configuración de bienestar")
        title.setObjectName("sectionTitle")
        values = QLabel(
            f"Pausa recomendada cada {config.RECOMMENDED_BREAK_INTERVAL_MINUTES} min\n"
            f"Aviso previo: {config.BREAK_WARNING_ADVANCE_MINUTES} min\n"
            f"Duración sugerida: {config.SUGGESTED_BREAK_DURATION_MINUTES} min\n"
            f"Recordar después: {config.POSTPONE_TIME_MINUTES} min"
        )
        values.setObjectName("mutedText")
        content.addWidget(title)
        content.addWidget(values)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _build_users(self):
        page, layout = self._page("Usuarios", "Cada perfil mantiene sus propias sesiones y pausas")
        header = QHBoxLayout()
        header.addWidget(QLabel("Selecciona el perfil que utilizará la aplicación"))
        header.addStretch()
        self.btn_create_user = QPushButton("Crear usuario")
        self.btn_create_user.setObjectName("primaryButton")
        self.btn_create_user.clicked.connect(self._show_create_user_dialog)
        header.addWidget(self.btn_create_user)
        layout.addLayout(header)
        self.users_container = QScrollArea()
        self.users_container.setWidgetResizable(True)
        users = QWidget()
        self.users_list_layout = QVBoxLayout(users)
        self.users_list_layout.addStretch()
        self.users_container.setWidget(users)
        layout.addWidget(self.users_container)
        return page

    def _navigate(self, index):
        if index == self.PAGE_USERS:
            self._load_users()
        if index == self.PAGE_HISTORY:
            self._load_history()
        self.pages.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)

    def _start_session(self):
        super()._start_session()
        if self.session_service and self.session_service.get_active_session():
            self._navigate(self.PAGE_WELLBEING)

    def _end_session(self, show_summary=True):
        super()._end_session(show_summary)
        self._navigate(self.PAGE_HOME)

    def _update_session_ui_state(self):
        super()._update_session_ui_state()
        active = bool(self.session_service and self.session_service.get_active_session())
        user = self.user_service.get_active_user() if self.user_service else None
        self.home_empty.setVisible(not user)
        self.home_content.setVisible(bool(user))
        self.wellbeing_empty.setVisible(not active)
        self.wellbeing_content.setVisible(active)
        self.btn_monitor_end.setVisible(active)
        if not active:
            self.lbl_status.setText("Sin sesión")
            self.lbl_home_level.setText("Sin sesión activa")

    def _update_active_user_display(self):
        super()._update_active_user_display()
        user = self.user_service.get_active_user() if self.user_service else None
        self.lbl_home_user.setText(f"Hola, {user.name}" if user else "Hola")

    def _update_session_time(self):
        if not self.wellbeing_service:
            return
        state = self.wellbeing_service.get_state()
        if not state:
            return
        from wellbeing.models import CycleState
        cycle = self.wellbeing_service.get_cycle_state()
        state_text = {
            CycleState.WORKING: "En buen ritmo",
            CycleState.BREAK_DUE_SOON: "Pausa próxima",
            CycleState.BREAK_DUE: "Es momento de una pausa",
            CycleState.BREAKING: "Pausa en curso",
        }[cycle]
        self.lbl_home_level.setText(state_text)
        self.lbl_wellbeing_state.setText(state_text)
        self.lbl_status.setText({
            CycleState.WORKING: "Trabajando",
            CycleState.BREAK_DUE_SOON: "Pausa recomendada pronto",
            CycleState.BREAK_DUE: "Pausa recomendada",
            CycleState.BREAKING: "En pausa",
        }[cycle])
        session_text = self._duration_text(state.session_elapsed_seconds)
        continuous_text = self._duration_text(state.continuous_usage_seconds)
        self.lbl_elapsed.setText(f"Tiempo de sesión: {session_text}")
        self.lbl_monitor_time.setText(f"Tiempo de sesión: {session_text}")
        self.lbl_continuous_usage.setText(f"Uso continuo: {continuous_text}")
        self.lbl_monitor_continuous.setText(f"Uso continuo: {continuous_text}")
        remaining = self.wellbeing_service.get_time_until_next_break()
        next_text = f"Próxima pausa en: {max(1, remaining // 60)} min"
        self.lbl_break_info.setText(next_text)
        self.lbl_monitor_next_break.setText(next_text)
        self.lbl_monitor_breaks.setText(
            f"Pausas realizadas en esta sesión: {state.completed_breaks}"
            if state.completed_breaks else "Aún no has realizado pausas en esta sesión."
        )
        self.break_reminder_card.setVisible(cycle == CycleState.BREAK_DUE)
        self.breaking_card.setVisible(cycle == CycleState.BREAKING)
        if cycle == CycleState.BREAK_DUE:
            self.lbl_reminder_body.setText(
                f"Llevas {state.continuous_usage_seconds // 60} minutos de uso continuo."
            )
            if not self._reminder_recommendation_visible:
                self._set_reminder_recommendation()
                self._reminder_recommendation_visible = True
        elif cycle == CycleState.BREAKING:
            started = self.wellbeing_service.get_break_started_at()
            self.lbl_breaking_since.setText(
                f"Desde: {started.strftime('%H:%M:%S')}" if started else ""
            )
            elapsed = self.wellbeing_service.get_break_elapsed_seconds()
            left = self.wellbeing_service.get_break_remaining_seconds()
            self.lbl_break_timer.setText(
                f"{left // 60:02d}:{left % 60:02d} restantes · "
                f"{elapsed // 60:02d}:{elapsed % 60:02d} transcurridos"
            )
            if started != self._recommendation_break_key:
                self._recommendation_break_key = started
                self._set_break_recommendations()
        else:
            self._reminder_recommendation_visible = False
            self._recommendation_break_key = None
        self.lbl_break_completed.setVisible(
            self.wellbeing_service.was_break_completed_recently()
            and cycle != CycleState.BREAKING
        )

    def _on_start_break(self):
        self.wellbeing_service.start_break()
        self._update_session_time()

    def _on_postpone(self):
        self.wellbeing_service.postpone()
        self._update_session_time()

    def _on_finish_break(self):
        self.wellbeing_service.complete_break()
        self._update_session_time()

    def _recommendation_context(self, break_active=False):
        from app import config
        from wellbeing.recommendations import RecommendationContext
        state = self.wellbeing_service.get_state()
        return RecommendationContext(
            continuous_usage_seconds=state.continuous_usage_seconds,
            break_active=break_active,
            break_duration_seconds=config.SUGGESTED_BREAK_DURATION_MINUTES * 60,
            completed_breaks=state.completed_breaks,
            postponed_breaks=state.postponed_breaks,
        )

    def _set_reminder_recommendation(self):
        if not self.recommendation_service:
            self.lbl_reminder_tip.setText(
                "Una pausa breve puede ayudarte a descansar la vista y cambiar de postura."
            )
            return
        self.lbl_reminder_tip.setText(
            self.recommendation_service.select(self._recommendation_context())[0].text
        )

    def _set_break_recommendations(self):
        if not self.recommendation_service:
            self.lbl_break_suggestions_title.hide()
            self.lbl_break_suggestions.clear()
            return
        selected = self.recommendation_service.select(
            self._recommendation_context(True), limit=2
        )
        self.lbl_break_suggestions_title.show()
        self.lbl_break_suggestions.setText(
            "\n".join(f"• {item.text}" for item in selected)
        )

    def _load_history(self):
        super()._load_history()
        user = self.user_service.get_active_user() if self.user_service else None
        analytics = self.wellbeing_analytics_service
        if not user or not analytics:
            self._empty_history_analytics()
            return
        week = analytics.period_stats(user.id, 7)
        month = analytics.period_stats(user.id, 30)
        self.lbl_week_sessions.setText(str(week.session_count))
        self.lbl_week_usage.setText(self._duration_text(week.total_usage_seconds))
        self.lbl_week_breaks.setText(str(week.completed_breaks))
        self.lbl_week_continuous.setText(
            self._duration_text(week.average_continuous_before_break_seconds)
            if week.average_continuous_before_break_seconds else "Sin datos"
        )
        self.lbl_period_summary.setText(
            f"Últimos 30 días: {month.session_count} sesiones · "
            f"{self._duration_text(month.total_usage_seconds)} de uso · "
            f"{self._duration_text(month.total_break_seconds)} en pausas · "
            f"{month.total_postponed_breaks} posposiciones.\n"
            f"{analytics.compare_weekly_breaks(user.id)}"
        )
        daily = analytics.daily_stats(user.id, 7)
        self._set_line_chart(
            self.chart_daily_usage, "Tiempo de uso por día",
            [(datetime.combine(day, datetime.min.time()), seconds / 3600)
             for day, seconds, _ in daily], "Horas",
        )
        self._set_line_chart(
            self.chart_daily_breaks, "Pausas realizadas por día",
            [(datetime.combine(day, datetime.min.time()), count)
             for day, _, count in daily], "Pausas",
        )

    def _empty_history_analytics(self):
        self.lbl_week_sessions.setText("0")
        self.lbl_week_usage.setText("00:00:00")
        self.lbl_week_breaks.setText("0")
        self.lbl_week_continuous.setText("Sin datos")
        self.lbl_period_summary.setText("Selecciona un usuario para consultar sus estadísticas.")
        self._set_line_chart(self.chart_daily_usage, "Tiempo de uso por día", [], "Horas")
        self._set_line_chart(self.chart_daily_breaks, "Pausas por día", [], "Pausas")

    def _create_user_widget(self, user):
        card = self._card()
        layout = QHBoxLayout(card)
        info = QVBoxLayout()
        name = QLabel(user.name)
        name.setObjectName("sectionTitle")
        info.addWidget(name)
        if user.created_at:
            try:
                created = datetime.fromisoformat(user.created_at).strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                created = str(user.created_at)
            info.addWidget(QLabel("Creado: " + created))
        layout.addLayout(info, 1)
        select = QPushButton("Seleccionar perfil")
        select.setObjectName("secondaryButton")
        select.clicked.connect(lambda: self._select_user(user))
        layout.addWidget(select)
        return card

    def _create_session_widget(self, session):
        card = self._card()
        layout = QHBoxLayout(card)
        text = QVBoxLayout()
        title = QLabel(
            session.started_at.strftime("%d/%m/%Y · %H:%M")
            if session.started_at else "Fecha desconocida"
        )
        title.setObjectName("sectionTitle")
        summary = (
            self.wellbeing_analytics_service.session_summary(session)
            if self.wellbeing_analytics_service else None
        )
        max_usage = (
            self._duration_text(summary.max_continuous_usage_seconds)
            if summary and summary.has_break_data else "Sin datos de pausas"
        )
        detail = QLabel(
            f"Duración: {self._duration_text(session.duration_seconds)} · "
            f"Pausas: {summary.completed_breaks if summary else 0} · "
            f"Uso continuo máximo: {max_usage}"
        )
        detail.setObjectName("mutedText")
        text.addWidget(title)
        text.addWidget(detail)
        layout.addLayout(text, 1)
        button = QPushButton("Ver detalle")
        button.setObjectName("secondaryButton")
        button.clicked.connect(lambda: self._show_session_detail(session))
        layout.addWidget(button)
        return card

    def _show_session_detail(self, session):
        summary = (
            self.wellbeing_analytics_service.session_summary(session)
            if self.wellbeing_analytics_service else None
        )
        if not summary or not summary.has_break_data:
            pauses = "Sin datos de pausas"
        else:
            pauses = "\n".join(
                f"  Pausa {index}: {self._duration_text(seconds)}"
                for index, seconds in enumerate(summary.break_durations_seconds, 1)
            ) or "Sin pausas completadas"
        self.lbl_session_detail.setText(
            f"Inicio: {session.started_at.strftime('%d/%m/%Y %H:%M') if session.started_at else '---'}\n"
            f"Término: {session.ended_at.strftime('%H:%M:%S') if session.ended_at else 'En curso'}\n"
            f"Duración total: {self._duration_text(session.duration_seconds)}\n"
            + (f"Tiempo de trabajo: {self._duration_text(summary.work_seconds)}\n"
               f"Tiempo en pausa: {self._duration_text(summary.break_seconds)}\n"
               f"Pausas realizadas: {summary.completed_breaks}\n"
               f"Pausas pospuestas: {summary.postponed_breaks}\n"
               f"Uso continuo máximo: {self._duration_text(summary.max_continuous_usage_seconds)}\n"
               f"Promedio de pausa: {self._duration_text(summary.average_break_seconds)}\n"
               if summary and summary.has_break_data else "")
            + f"Detalle de pausas:\n{pausas}"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = event.size().width() < 1000
        if compact:
            self.home_cards_layout.addWidget(self.home_welcome_card, 0, 0)
            self.home_cards_layout.addWidget(self.home_state_card, 1, 0)
            self.history_content_layout.setDirection(QHBoxLayout.TopToBottom)
            self.history_charts_layout.addWidget(self.chart_daily_usage, 0, 0)
            self.history_charts_layout.addWidget(self.chart_daily_breaks, 1, 0)
        else:
            self.home_cards_layout.addWidget(self.home_welcome_card, 0, 0)
            self.home_cards_layout.addWidget(self.home_state_card, 0, 1)
            self.history_content_layout.setDirection(QHBoxLayout.LeftToRight)
            self.history_charts_layout.addWidget(self.chart_daily_usage, 0, 0)
            self.history_charts_layout.addWidget(self.chart_daily_breaks, 0, 1)

    @staticmethod
    def _duration_text(value):
        seconds = max(0, int(value or 0))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _centered(text):
        label = QLabel(text)
        label.setObjectName("sessionTime")
        label.setAlignment(Qt.AlignCenter)
        return label

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
        return _MetricCard(card, value_label)

    @staticmethod
    def _empty_state(title, subtitle):
        frame = QFrame()
        frame.setObjectName("emptyState")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        heading.setAlignment(Qt.AlignCenter)
        caption = QLabel(subtitle)
        caption.setObjectName("mutedText")
        caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)
        layout.addWidget(caption)
        return frame

    @staticmethod
    def _create_chart_view():
        from ui.theme import style_chart
        view = DashboardWidget._create_chart_view()
        style_chart(view.chart())
        view.setRenderHint(QPainter.Antialiasing)
        return view

    @staticmethod
    def _set_line_chart(view, title, points, y_title):
        from ui.theme import style_chart
        DashboardWidget._set_line_chart(view, title, points, y_title)
        style_chart(view.chart())

    @staticmethod
    def _theme():
        from ui.theme import QSS
        return QSS


class _MetricCard(QFrame):
    def __init__(self, card, value_label):
        super().__init__()
        self.setObjectName("card")
        self._value_label = value_label
        layout = QVBoxLayout(self)
        source = card.layout()
        while source.count():
            item = source.takeAt(0)
            if item.widget():
                item.widget().setParent(self)
                layout.addWidget(item.widget())

    def setText(self, text):
        self._value_label.setText(text.split(":", 1)[-1].strip())

    def text(self):
        return self._value_label.text()
