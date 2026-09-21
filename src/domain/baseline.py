import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class BaselineState(Enum):
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CALIBRATING = "CALIBRATING"
    READY = "READY"

class WelfordAccumulator:
    """
    Cálculo incremental de media y desviación estándar usando el algoritmo de Welford.
    No guarda todos los valores en memoria.
    """
    def __init__(self):
        self.n = 0
        self._mean = 0.0
        self._M2 = 0.0

    def add(self, value: float) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
        value = float(value)
        self.n += 1
        delta = value - self._mean
        self._mean += delta / self.n
        delta2 = value - self._mean
        self._M2 += delta * delta2
        return True

    @property
    def mean(self) -> Optional[float]:
        return self._mean if self.n > 0 else None

    @property
    def variance(self) -> Optional[float]:
        if self.n < 2:
            return None
        return self._M2 / (self.n - 1)

    @property
    def std(self) -> Optional[float]:
        v = self.variance
        return math.sqrt(v) if v is not None and v >= 0 else None

    def restore(self, n: int, mean: float, m2: float):
        """Restaurar desde valores guardados en SQLite."""
        if n < 0 or not all(math.isfinite(v) for v in (mean, m2)):
            raise ValueError("Estadísticas de baseline inválidas")
        self.n = int(n)
        self._mean = float(mean)
        self._M2 = float(m2)

    def to_tuple(self) -> tuple:
        """Serializar para persistencia: (n, mean, M2)."""
        return (self.n, self._mean, self._M2)


@dataclass
class MetricBaseline:
    mean: Optional[float]
    std: Optional[float]
    n_samples: int

    def deviation(self, value: float) -> Optional[dict]:
        """
        Calcula desviaciones respecto al baseline.
        Devuelve None si no hay datos suficientes.
        Nunca convierte ausencia en 0.
        """
        if (self.mean is None or self.n_samples == 0 or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value)):
            return None
        difference = float(value) - self.mean
        pct_change = (difference / self.mean * 100) if self.mean != 0 else None
        z_score = (difference / self.std) if self.std and self.std > 0 else None
        return {
            "absolute": abs(difference),
            "percent": pct_change,
            "z_score": z_score
        }


@dataclass
class UserBaseline:
    user_id: int
    state: BaselineState = BaselineState.INSUFFICIENT_DATA
    # Métricas con sus acumuladores Welford internos
    ear: Optional[MetricBaseline] = None
    blink_rate: Optional[MetricBaseline] = None
    blink_duration: Optional[MetricBaseline] = None
    perclos: Optional[MetricBaseline] = None
    mar: Optional[MetricBaseline] = None
    pitch: Optional[MetricBaseline] = None
    yaw: Optional[MetricBaseline] = None
    roll: Optional[MetricBaseline] = None
