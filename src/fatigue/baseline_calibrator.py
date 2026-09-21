import math
from typing import Optional
from fatigue.baseline import (
    BaselineState, WelfordAccumulator, MetricBaseline, UserBaseline
)
from fatigue.models import EyeState, MouthState

class BaselineCalibratorConfig:
    MIN_FRAME_SAMPLES_READY = 300  # EAR, MAR y pose (~10s a 30fps)
    MIN_BLINK_SAMPLES_READY = 3
    MIN_RATE_SAMPLES_READY = 3
    MIN_PERCLOS_SAMPLES_READY = 30

    def __init__(self, frame_samples=300, blink_samples=3, rate_samples=3, perclos_samples=30):
        self.frame_samples = frame_samples
        self.blink_samples = blink_samples
        self.rate_samples = rate_samples
        self.perclos_samples = perclos_samples

class BaselineCalibrator:
    """
    Recopila muestras válidas frame a frame para construir un baseline personal.
    Usa algoritmo de Welford para estadísticas incrementales sin guardar todos los valores.
    """

    def __init__(self, user_id: int, config: Optional[BaselineCalibratorConfig] = None):
        self.user_id = user_id
        self.config = config or BaselineCalibratorConfig()
        self._state = BaselineState.INSUFFICIENT_DATA

        # Un acumulador por métrica
        self._ear = WelfordAccumulator()
        self._mar = WelfordAccumulator()
        self._pitch = WelfordAccumulator()
        self._yaw = WelfordAccumulator()
        self._roll = WelfordAccumulator()
        self._blink_duration = WelfordAccumulator()
        self._blink_rate_samples = WelfordAccumulator()
        self._perclos_samples = WelfordAccumulator()

    def _update_state(self):
        counts = self._counts()
        if all(counts[name] >= minimum for name, minimum in self._minimums().items()):
            self._state = BaselineState.READY
        elif any(counts.values()):
            self._state = BaselineState.CALIBRATING
        else:
            self._state = BaselineState.INSUFFICIENT_DATA

    def _counts(self):
        return {
            "ear": self._ear.n, "mar": self._mar.n,
            "pitch": self._pitch.n, "yaw": self._yaw.n, "roll": self._roll.n,
            "blink_duration": self._blink_duration.n,
            "blink_rate": self._blink_rate_samples.n,
            "perclos": self._perclos_samples.n,
        }

    def _minimums(self):
        return {
            "ear": self.config.frame_samples, "mar": self.config.frame_samples,
            "pitch": self.config.frame_samples, "yaw": self.config.frame_samples,
            "roll": self.config.frame_samples,
            "blink_duration": self.config.blink_samples,
            "blink_rate": self.config.rate_samples,
            "perclos": self.config.perclos_samples,
        }

    @staticmethod
    def _finite(value) -> bool:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value))

    def add_ear_sample(self, ear: Optional[float], eye_state: EyeState):
        """Solo muestras con ojos ABIERTOS son válidas para el EAR de referencia."""
        if not self._finite(ear) or eye_state != EyeState.OPEN:
            return
        if not (0.0 < ear < 1.0):
            return
        self._ear.add(ear)
        self._update_state()

    def add_mar_sample(self, mar: Optional[float], mouth_state: MouthState):
        """Solo muestras con boca CERRADA son válidas para el MAR de referencia."""
        if not self._finite(mar) or mouth_state != MouthState.CLOSED:
            return
        if not (0.0 <= mar < 2.0):
            return
        self._mar.add(mar)
        self._update_state()

    def add_head_pose_sample(self, pitch: Optional[float], yaw: Optional[float], roll: Optional[float]):
        if not all(self._finite(v) for v in (pitch, yaw, roll)):
            return
        if any(abs(v) > 90 for v in [pitch, yaw, roll]):
            return  # Valores extremos son probablemente artefactos
        self._pitch.add(pitch)
        self._yaw.add(yaw)
        self._roll.add(roll)
        self._update_state()

    def add_blink_duration(self, duration: float):
        if not self._finite(duration) or duration <= 0 or duration > 1.0:
            return
        self._blink_duration.add(duration)
        self._update_state()

    def add_blink_rate(self, bpm: float):
        if not self._finite(bpm) or bpm <= 0 or bpm > 60:
            return
        self._blink_rate_samples.add(bpm)
        self._update_state()

    def add_perclos_sample(self, perclos: Optional[float]):
        if not self._finite(perclos):
            return
        if not (0.0 <= perclos <= 1.0):
            return
        self._perclos_samples.add(perclos)
        self._update_state()

    @property
    def state(self) -> BaselineState:
        return self._state

    @property
    def progress(self) -> float:
        """Progreso 0.0–1.0 hacia MIN_SAMPLES_READY para la métrica más lenta."""
        ratios = [self._counts()[name] / minimum for name, minimum in self._minimums().items()]
        return min(min(ratios), 1.0)

    def _to_metric(self, acc: WelfordAccumulator) -> Optional[MetricBaseline]:
        if acc.n == 0:
            return None
        return MetricBaseline(mean=acc.mean, std=acc.std, n_samples=acc.n)

    def build_baseline(self) -> UserBaseline:
        return UserBaseline(
            user_id=self.user_id,
            state=self._state,
            ear=self._to_metric(self._ear),
            blink_rate=self._to_metric(self._blink_rate_samples),
            blink_duration=self._to_metric(self._blink_duration),
            perclos=self._to_metric(self._perclos_samples),
            mar=self._to_metric(self._mar),
            pitch=self._to_metric(self._pitch),
            yaw=self._to_metric(self._yaw),
            roll=self._to_metric(self._roll),
        )

    def restore_from_baseline(self, baseline: UserBaseline):
        """Restaurar el estado del calibrador desde un baseline guardado en SQLite."""
        self._state = baseline.state
        # Restauramos solo n y mean; M2 se estima de std y n para continuar acumulando
        def _restore(acc: WelfordAccumulator, mb: Optional[MetricBaseline]):
            if mb and mb.n_samples > 0 and mb.mean is not None:
                variance = (mb.std ** 2) if mb.std else 0.0
                m2 = variance * (mb.n_samples - 1)
                acc.restore(mb.n_samples, mb.mean, m2)
        _restore(self._ear, baseline.ear)
        _restore(self._mar, baseline.mar)
        _restore(self._pitch, baseline.pitch)
        _restore(self._yaw, baseline.yaw)
        _restore(self._roll, baseline.roll)
        _restore(self._blink_duration, baseline.blink_duration)
        _restore(self._blink_rate_samples, baseline.blink_rate)
        _restore(self._perclos_samples, baseline.perclos)
        self._update_state()
