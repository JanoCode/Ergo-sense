import logging

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

logger = logging.getLogger(__name__)


class DashboardWidget(QWidget):
    """Shared UI orchestration for the active digital-wellbeing flow."""

    def __init__(self, user_service=None, session_service=None,
                 wellbeing_service=None, recommendation_service=None,
                 wellbeing_analytics_service=None):
        super().__init__()
        self.user_service = user_service
        self.session_service = session_service
        self.wellbeing_service = wellbeing_service
        self.recommendation_service = recommendation_service
        self.wellbeing_analytics_service = wellbeing_analytics_service
        self._recommendation_break_key = None
        self._reminder_recommendation_visible = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_session_time)
        self._setup_ui()
        self._load_users()
        self._update_active_user_display()

    def _setup_ui(self):
        raise NotImplementedError

    def _load_users(self):
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
            for user in users:
                self.users_list_layout.insertWidget(
                    self.users_list_layout.count() - 1,
                    self._create_user_widget(user),
                )
        except Exception:
            logger.exception("Failed to load users")
            self._show_empty_users_message("No se pudieron cargar los usuarios.")

    def _show_empty_users_message(self, message="No hay usuarios registrados."):
        label = QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("mutedText")
        self.users_list_layout.insertWidget(0, label)

    def _show_create_user_dialog(self):
        from users.ui import CreateUserDialog
        if not self.user_service:
            return
        dialog = CreateUserDialog(self.user_service, self)
        if dialog.exec():
            self._load_users()

    def _select_user(self, user):
        if self.session_service and self.session_service.get_active_session():
            QMessageBox.warning(
                self, "Sesión activa",
                "Finaliza la sesión actual antes de cambiar de usuario.",
            )
            return
        self.user_service.set_active_user(user)
        self._update_active_user_display()

    def _update_active_user_display(self):
        user = self.user_service.get_active_user() if self.user_service else None
        self.lbl_active_user.setText(
            f"Usuario activo: {user.name}" if user else "No hay usuario activo"
        )
        self._update_session_ui_state()
        self._load_history()

    def _load_history(self):
        while self.history_list_layout.count() > 1:
            item = self.history_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        user = self.user_service.get_active_user() if self.user_service else None
        if not user or not self.session_service:
            self.lbl_session_count.setText("Sesiones registradas: 0")
            self._show_empty_history_message("Selecciona un usuario.")
            return
        sessions = self.session_service.get_user_sessions(user.id)
        self.lbl_session_count.setText(f"Sesiones registradas: {len(sessions)}")
        if not sessions:
            self._show_empty_history_message("Todavía no hay sesiones registradas.")
            return
        for session in sessions:
            self.history_list_layout.insertWidget(
                self.history_list_layout.count() - 1,
                self._create_session_widget(session),
            )

    def _show_empty_history_message(self, message):
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("mutedText")
        self.history_list_layout.insertWidget(0, label)

    def _start_session(self):
        if not self.session_service:
            return
        try:
            self.session_service.start_session()
            self.timer.start(1000)
            self._update_session_ui_state()
            self._update_session_time()
        except Exception as error:
            QMessageBox.warning(self, "Error al iniciar", str(error))

    def _end_session(self, show_summary=True):
        del show_summary
        if not self.session_service:
            return
        try:
            if self.wellbeing_service:
                self.wellbeing_service.end_active_break()
            self.session_service.end_session()
            self.timer.stop()
            self._update_session_ui_state()
            self._load_history()
        except Exception as error:
            QMessageBox.warning(self, "Error al finalizar", str(error))

    def _update_session_ui_state(self):
        active = bool(
            self.session_service and self.session_service.get_active_session()
        )
        user = self.user_service.get_active_user() if self.user_service else None
        self.btn_start_session.setVisible(not active)
        self.btn_start_session.setEnabled(user is not None)
        self.btn_end_session.setVisible(active)

    def _update_session_time(self):
        return

    def shutdown(self):
        self.timer.stop()
        if self.session_service and self.session_service.get_active_session():
            self._end_session(show_summary=False)

    @staticmethod
    def _create_chart_view():
        view = QChartView()
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(220)
        return view

    @staticmethod
    def _set_line_chart(view, title, points, y_title):
        chart = QChart()
        chart.legend().hide()
        chart.setTitle(title if points else f"{title} — Sin datos disponibles")
        if points:
            series = QLineSeries()
            for timestamp, value in points:
                qdatetime = QDateTime.fromSecsSinceEpoch(int(timestamp.timestamp()))
                series.append(qdatetime.toMSecsSinceEpoch(), value)
            chart.addSeries(series)
            axis_x = QDateTimeAxis()
            axis_x.setFormat("dd/MM")
            axis_x.setTitleText("Fecha")
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            values = [value for _, value in points]
            low, high = min(values), max(values)
            padding = max((high - low) * 0.1, 1.0)
            axis_y = QValueAxis()
            axis_y.setTitleText(y_title)
            axis_y.setLabelFormat("%.1f")
            axis_y.setRange(max(0.0, low - padding), high + padding)
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
        view.setChart(chart)
