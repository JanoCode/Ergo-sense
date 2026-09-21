import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

from fatigue.models import EyeState
from fatigue.perclos import PerclosCalculator, ProlongedClosureDetector, ProlongedClosureConfig

class TestPerclosCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = PerclosCalculator(window_60s=60.0, window_5min=300.0)

    def test_perclos_no_data(self):
        result = self.calc.get_perclos(100.0)
        self.assertIsNone(result.perclos_60s)
        self.assertIsNone(result.perclos_5min)

    def test_perclos_insufficient_data(self):
        # Solo 5s de datos (menos que MIN_VALID_SECONDS=10)
        self.calc.add_event(100.0, EyeState.CLOSED, 5.0)
        result = self.calc.get_perclos(100.0)
        self.assertIsNone(result.perclos_60s)

    def test_perclos_excludes_unknown(self):
        # Si solo hay UNKNOWN, no debe computar
        calc = PerclosCalculator()
        calc.add_event(100.0, EyeState.UNKNOWN, 30.0)  # no se registra internamente
        result = calc.get_perclos(100.0)
        self.assertIsNone(result.perclos_60s)

    def test_perclos_50_percent(self):
        # 15s cerrado + 15s abierto = 30s válidos; PERCLOS = 50%
        now = 200.0
        self.calc.add_event(170.0, EyeState.CLOSED, 15.0)
        self.calc.add_event(185.0, EyeState.OPEN, 15.0)
        result = self.calc.get_perclos(now)
        self.assertAlmostEqual(result.perclos_60s, 0.5)

    def test_perclos_window_excludes_old_events(self):
        calc = PerclosCalculator(window_60s=60.0, window_5min=300.0)
        # Evento muy antiguo (fuera de ventana 60s)
        calc.add_event(10.0, EyeState.CLOSED, 15.0)
        # Eventos recientes con suficiente datos
        now = 200.0
        calc.add_event(180.0, EyeState.OPEN, 20.0)
        result = calc.get_perclos(now)
        # Solo hay 20s de datos abiertos → PERCLOS = 0%
        self.assertAlmostEqual(result.perclos_60s, 0.0)

    def test_perclos_5min_includes_more(self):
        # Evento hace 2 minutos = fuera de 60s pero dentro de 5min
        now = 300.0
        self.calc.add_event(175.0, EyeState.CLOSED, 15.0)  # hace ~125s
        self.calc.add_event(190.0, EyeState.OPEN, 15.0)    # hace ~110s
        result = self.calc.get_perclos(now)
        self.assertIsNone(result.perclos_60s)
        self.assertAlmostEqual(result.perclos_5min, 0.5)


class TestProlongedClosureDetector(unittest.TestCase):
    def setUp(self):
        config = ProlongedClosureConfig()
        config.PROLONGED_THRESHOLD_SECONDS = 1.5
        self.det = ProlongedClosureDetector(config)

    def test_normal_blink_not_counted(self):
        self.det.process_state(EyeState.OPEN, 0.0)
        self.det.process_state(EyeState.CLOSED, 1.0)
        self.det.process_state(EyeState.OPEN, 1.1)  # 0.1s < 1.5s threshold
        result = self.det.get_result(1.1)
        self.assertEqual(result.count, 0)

    def test_prolonged_closure_counted_on_open(self):
        self.det.process_state(EyeState.OPEN, 0.0)
        self.det.process_state(EyeState.CLOSED, 1.0)
        self.det.process_state(EyeState.OPEN, 3.0)  # 2.0s > 1.5s
        result = self.det.get_result(3.0)
        self.assertEqual(result.count, 1)
        self.assertAlmostEqual(result.max_duration, 2.0)

    def test_no_double_count_while_closed(self):
        self.det.process_state(EyeState.OPEN, 0.0)
        self.det.process_state(EyeState.CLOSED, 1.0)
        # Múltiples frames mientras sigue cerrado
        self.det.process_state(EyeState.CLOSED, 2.0)
        self.det.process_state(EyeState.CLOSED, 3.0)
        self.det.process_state(EyeState.CLOSED, 4.0)
        result = self.det.get_result(4.0)
        # Solo debe haberse contado una vez al superar el umbral
        self.assertEqual(result.count, 1)

    def test_current_duration_while_closed(self):
        self.det.process_state(EyeState.OPEN, 0.0)
        self.det.process_state(EyeState.CLOSED, 10.0)
        duration = self.det.get_current_closure_duration(12.5)
        self.assertAlmostEqual(duration, 2.5)

    def test_unknown_ignored(self):
        self.det.process_state(EyeState.OPEN, 0.0)
        self.det.process_state(EyeState.CLOSED, 1.0)
        self.det.process_state(EyeState.UNKNOWN, 2.0)
        # El cierre no debe reiniciarse por UNKNOWN
        self.det.process_state(EyeState.OPEN, 3.0)
        # No alcanzó el umbral en tiempo de cierre puro (excluye UNKNOWN)
        # pero el closed_start no fue reseteado, así que 3.0-1.0=2.0s >= 1.5s
        result = self.det.get_result(3.0)
        self.assertEqual(result.count, 1)

if __name__ == '__main__':
    unittest.main()
