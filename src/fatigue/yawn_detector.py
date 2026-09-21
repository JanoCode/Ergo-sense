from typing import Optional
from fatigue.models import MouthState, YawnMetrics

class YawnConfig:
    MIN_OPEN_SECONDS = 2.0      # Mínimo tiempo boca abierta para ser bostezo
    MAX_YAWN_SECONDS = 10.0     # Máximo razonable (más es probablemente UNKNOWN drift)

class YawnDetector:
    def __init__(self, config: YawnConfig = YawnConfig()):
        self.config = config
        self.total_yawns = 0
        self.last_duration = 0.0
        self.total_duration = 0.0

        self._is_open = False
        self._open_start: Optional[float] = None
        self._already_counted = False
        self._session_start: float = 0.0

    def reset(self, session_start: float):
        self.total_yawns = 0
        self.last_duration = 0.0
        self.total_duration = 0.0
        self._is_open = False
        self._open_start = None
        self._already_counted = False
        self._session_start = session_start

    def process_state(self, state: MouthState, current_time: float):
        if state == MouthState.UNKNOWN:
            return

        if state == MouthState.OPEN:
            if not self._is_open:
                self._is_open = True
                self._open_start = current_time
                self._already_counted = False
            else:
                # Verificar si supera el umbral por primera vez (conteo durante apertura)
                if not self._already_counted and self._open_start is not None:
                    duration = current_time - self._open_start
                    if duration >= self.config.MIN_OPEN_SECONDS:
                        self.total_yawns += 1
                        self._already_counted = True
        else:  # CLOSED
            if self._is_open and self._open_start is not None:
                duration = current_time - self._open_start
                if self.config.MIN_OPEN_SECONDS <= duration <= self.config.MAX_YAWN_SECONDS:
                    self.last_duration = duration
                    self.total_duration += duration
                    if not self._already_counted:
                        self.total_yawns += 1
                elif duration > self.config.MAX_YAWN_SECONDS:
                    pass  # Ignorar: probablemente datos espurios
            self._is_open = False
            self._open_start = None
            self._already_counted = False

    def get_current_duration(self, current_time: float) -> float:
        if self._is_open and self._open_start is not None:
            return current_time - self._open_start
        return 0.0

    def get_metrics(self, current_time: float) -> YawnMetrics:
        elapsed_hours = (current_time - self._session_start) / 3600.0
        yph = self.total_yawns / elapsed_hours if elapsed_hours > 0 else 0.0
        avg = self.total_duration / self.total_yawns if self.total_yawns > 0 else 0.0
        return YawnMetrics(
            total_yawns=self.total_yawns,
            current_duration=self.get_current_duration(current_time),
            last_duration=self.last_duration,
            avg_duration=avg,
            yawns_per_hour=yph
        )
