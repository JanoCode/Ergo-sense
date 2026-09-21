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


if __name__ == "__main__":
    unittest.main()
