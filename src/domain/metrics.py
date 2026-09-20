from enum import Enum
from dataclasses import dataclass
from typing import Optional

class EyeState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

@dataclass
class EyeMetricsResult:
    ear_left: Optional[float]
    ear_right: Optional[float]
    ear_avg: Optional[float]
    state: EyeState

@dataclass
class BlinkMetrics:
    total_blinks: int
    last_blink_duration: float
    avg_blink_duration: float
    blinks_per_minute: float
