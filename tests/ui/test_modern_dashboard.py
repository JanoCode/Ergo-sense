import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src")
)

from PySide6.QtWidgets import QApplication, QLabel

from ui.modern_dashboard import ModernDashboardWidget
from sessions.models import Session
from wellbeing.models import CycleState, WellbeingSessionState


class TestModernDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dashboard = ModernDashboardWidget()
        self.dashboard.resize(760, 560)
        self.dashboard.show()
        self.app.processEvents()

    def tearDown(self):
        self.dashboard.close()
        self.dashboard.deleteLater()
        self.app.processEvents()

    def test_navigation_and_empty_state(self):
        self.assertEqual(self.dashboard.pages.count(), 5)
        self.assertTrue(self.dashboard.home_empty.isVisible())
        self.assertFalse(self.dashboard.home_content.isVisible())

        for index in range(5):
            self.dashboard._navigate(index)
            self.assertEqual(self.dashboard.pages.currentIndex(), index)

        self.dashboard.resize(1440, 900)
        self.app.processEvents()
        self.assertEqual(self.dashboard.pages.count(), 5)

    def test_navigation_uses_wellbeing_language(self):
        self.assertEqual(
            [button.text() for button in self.dashboard.nav_buttons],
            ["Inicio", "Bienestar", "Historial", "Configuración", "Usuarios"],
        )

    def _dashboard_for_cycle(self, cycle):
        started_at = datetime(2026, 9, 28, 10, 0, 0)
        session = Session(id=1, user_id=1, started_at=started_at)
        sessions = Mock()
        sessions.get_active_session.return_value = session
        sessions.get_user_sessions.return_value = []
        users = Mock()
        users.get_active_user.return_value = Mock(id=1, name="Ada")
        users.get_all_users.return_value = []
        wellbeing = Mock()
        wellbeing.get_state.return_value = WellbeingSessionState(
            session_id=1,
            session_started_at=started_at,
            continuous_usage_started_at=started_at,
            session_elapsed_seconds=3600,
            continuous_usage_seconds=3000,
        )
        wellbeing.get_cycle_state.return_value = cycle
        wellbeing.get_time_until_next_break.return_value = 300
        wellbeing.is_reminder_active.return_value = cycle == CycleState.BREAK_DUE
        wellbeing.should_show_reminder.return_value = cycle == CycleState.BREAK_DUE
        wellbeing.get_break_started_at.return_value = started_at
        wellbeing.get_break_remaining_seconds.return_value = 240
        wellbeing.get_break_elapsed_seconds.return_value = 60
        wellbeing.was_break_completed_recently.return_value = False
        dashboard = ModernDashboardWidget(
            user_service=users,
            session_service=sessions,
            wellbeing_service=wellbeing,
        )
        dashboard.show()
        self.app.processEvents()
        return dashboard

    def test_visual_states_follow_wellbeing_cycle(self):
        expected = {
            CycleState.WORKING: "En buen ritmo",
            CycleState.BREAK_DUE_SOON: "Pausa próxima",
            CycleState.BREAK_DUE: "Es momento de una pausa",
            CycleState.BREAKING: "Pausa en curso",
        }
        for cycle, label in expected.items():
            with self.subTest(cycle=cycle):
                dashboard = self._dashboard_for_cycle(cycle)
                dashboard._update_session_time()
                self.assertEqual(dashboard.lbl_home_level.text(), label)
                self.assertEqual(
                    dashboard.break_reminder_card.isVisible(),
                    cycle == CycleState.BREAK_DUE,
                )
                self.assertEqual(
                    dashboard.breaking_card.isVisible(),
                    cycle == CycleState.BREAKING,
                )
                self.assertEqual(
                    dashboard.btn_finish_break.isVisible(),
                    cycle == CycleState.BREAKING,
                )
                self.assertEqual(
                    dashboard.btn_start_break.isVisible(),
                    cycle == CycleState.BREAK_DUE,
                )
                self.assertEqual(
                    dashboard.btn_postpone.isVisible(),
                    cycle == CycleState.BREAK_DUE,
                )
                self.assertIn("Uso continuo:", dashboard.lbl_monitor_continuous.text())
                dashboard.close()
                dashboard.deleteLater()

    def test_history_remains_accessible(self):
        self.dashboard._navigate(self.dashboard.PAGE_HISTORY)
        self.assertEqual(
            self.dashboard.pages.currentIndex(), self.dashboard.PAGE_HISTORY
        )
        self.assertTrue(self.dashboard.history_container.isVisible())

    def test_no_legacy_fatigue_terms_are_visible_in_primary_view(self):
        forbidden = ("fatigue", "perclos", "ear:", "confianza", "baseline")
        visible_text = " ".join(
            label.text().lower()
            for label in self.dashboard.findChildren(QLabel)
            if label.isVisible()
        )
        for term in forbidden:
            self.assertNotIn(term, visible_text)

    def test_empty_and_populated_charts_keep_dark_palette(self):
        from datetime import datetime
        from ui.theme import SURFACE
        chart = self.dashboard.chart_daily_usage
        self.assertEqual(chart.chart().backgroundBrush().color().name(), SURFACE)
        for points in ([], [(datetime.now(), 32)]):
            self.dashboard._set_line_chart(chart, "Tiempo de uso", points, "Horas")
            self.assertEqual(chart.chart().backgroundBrush().color().name(), SURFACE)


if __name__ == "__main__":
    unittest.main()
