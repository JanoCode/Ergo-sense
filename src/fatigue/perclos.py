from collections import deque
from typing import Optional
from fatigue.models import EyeState, PerclosResult, ProlongedClosureResult

class ProlongedClosureConfig:
    # Tiempo mínimo cerrado para considerarse cierre prolongado (no parpadeo)
    PROLONGED_THRESHOLD_SECONDS = 1.5

class PerclosCalculator:
    """
    Calcula PERCLOS usando una ventana temporal deslizante.
    PERCLOS = tiempo válido con ojos cerrados / tiempo válido total
    Los períodos UNKNOWN son excluidos del denominador.
    """
    MIN_VALID_SECONDS = 10.0  # Mínimo para considerar que hay suficientes datos

    def __init__(self, window_60s=60.0, window_5min=300.0):
        self.window_60s = window_60s
        self.window_5min = window_5min
        # deque de (timestamp, state, duration_seconds)
        # donde duration_seconds es el tiempo que duró ese estado
        self._events: deque = deque()

    def reset(self):
        self._events.clear()

    def add_event(self, timestamp: float, state: EyeState, duration: float):
        """Registrar un intervalo de tiempo con un estado dado."""
        if state == EyeState.UNKNOWN or duration <= 0:
            return
        self._events.append((timestamp, state, duration))
        self._purge_old(timestamp)

    def _purge_old(self, now: float):
        cutoff = now - self.window_5min
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def _perclos_for_window(self, now: float, window: float) -> Optional[float]:
        cutoff = now - window
        closed_time = 0.0
        valid_time = 0.0
        for ts, state, dur in self._events:
            if ts < cutoff:
                continue
            valid_time += dur
            if state == EyeState.CLOSED:
                closed_time += dur
        if valid_time < self.MIN_VALID_SECONDS:
            return None
        return closed_time / valid_time

    def get_perclos(self, now: float) -> PerclosResult:
        return PerclosResult(
            perclos_60s=self._perclos_for_window(now, self.window_60s),
            perclos_5min=self._perclos_for_window(now, self.window_5min)
        )


class ProlongedClosureDetector:
    """
    Detecta cierres oculares prolongados (más allá del umbral de parpadeo normal).
    Evita contar el mismo cierre prolongado más de una vez mientras los ojos 
    permanecen cerrados.
    """

    def __init__(self, config: ProlongedClosureConfig = ProlongedClosureConfig()):
        self.config = config
        self.count = 0
        self.max_duration = 0.0
        self.total_duration = 0.0

        self._is_closed = False
        self._closed_start: Optional[float] = None
        self._already_counted = False  # Flag para evitar contar duplicados

    def reset(self):
        self.count = 0
        self.max_duration = 0.0
        self.total_duration = 0.0
        self._is_closed = False
        self._closed_start = None
        self._already_counted = False

    def process_state(self, state: EyeState, current_time: float):
        if state == EyeState.UNKNOWN:
            return

        if state == EyeState.CLOSED:
            if not self._is_closed:
                self._is_closed = True
                self._closed_start = current_time
                self._already_counted = False
            else:
                # Ya está cerrado, verificar si supera el umbral por primera vez
                if not self._already_counted and self._closed_start is not None:
                    duration = current_time - self._closed_start
                    if duration >= self.config.PROLONGED_THRESHOLD_SECONDS:
                        self.count += 1
                        self._already_counted = True
        else:  # OPEN
            if self._is_closed and self._closed_start is not None:
                duration = current_time - self._closed_start
                if duration >= self.config.PROLONGED_THRESHOLD_SECONDS:
                    self.max_duration = max(self.max_duration, duration)
                    self.total_duration += duration
                    if not self._already_counted:
                        self.count += 1
            self._is_closed = False
            self._closed_start = None
            self._already_counted = False

    def get_current_closure_duration(self, current_time: float) -> float:
        if self._is_closed and self._closed_start is not None:
            return current_time - self._closed_start
        return 0.0

    def get_result(self, current_time: float) -> ProlongedClosureResult:
        avg = self.total_duration / self.count if self.count > 0 else 0.0
        return ProlongedClosureResult(
            count=self.count,
            current_duration=self.get_current_closure_duration(current_time),
            max_duration=self.max_duration,
            avg_duration=avg
        )
