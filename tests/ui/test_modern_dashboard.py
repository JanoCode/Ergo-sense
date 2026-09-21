import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src")
)

from PySide6.QtWidgets import QApplication

from ui.modern_dashboard import ModernDashboardWidget


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

    def test_score_uses_plain_language_and_semantic_value(self):
        self.dashboard.lbl_fatigue_score.setText("Fatigue Score: 32/100")
        self.dashboard.lbl_fatigue_level.setText("Nivel: MILD")
        self.dashboard._sync_score()

        self.assertEqual(self.dashboard.lbl_home_score.text(), "32 / 100")
        self.assertEqual(self.dashboard.home_score_bar.value(), 32)
        self.assertEqual(self.dashboard.lbl_home_level.text(), "Nivel: Leve")

    def test_monitoring_controls_have_clear_labels(self):
        self.assertEqual(
            self.dashboard.advanced_toggle.text(), "Ver métricas avanzadas"
        )
        self.assertEqual(
            self.dashboard.lbl_head_dev.text(), "Esperando detección facial"
        )
        self.dashboard.advanced_toggle.setChecked(True)
        self.assertEqual(
            self.dashboard.advanced_toggle.text(), "Ocultar métricas avanzadas"
        )

    def test_empty_and_populated_charts_keep_dark_palette(self):
        from datetime import datetime
        from ui.theme import SURFACE
        chart = self.dashboard.chart_score
        self.assertEqual(chart.chart().backgroundBrush().color().name(), SURFACE)
        for points in ([], [(datetime.now(), 32)]):
            self.dashboard._set_line_chart(chart, "Score", points, "Score")
            self.assertEqual(chart.chart().backgroundBrush().color().name(), SURFACE)

    def test_metric_card_preserves_value_and_interpretation(self):
        card = self.dashboard.lbl_bpm
        card.setText("Parpadeos: 13.6/min")
        card.setInterpretation("Dentro de tu rango habitual")
        self.assertEqual(card.text(), "13.6/min")
        self.assertEqual(card._interpretation.text(), "Dentro de tu rango habitual")


if __name__ == "__main__":
    unittest.main()
