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

@dataclass
class PerclosResult:
    perclos_60s: Optional[float]
    perclos_5min: Optional[float]

@dataclass
class ProlongedClosureResult:
    count: int
    current_duration: float
    max_duration: float
    avg_duration: float

class MouthState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

@dataclass
class YawnMetrics:
    total_yawns: int
    current_duration: float
    last_duration: float
    avg_duration: float
    yawns_per_hour: float

@dataclass
class HeadPoseAngles:
    pitch: float
    yaw: float
    roll: float

@dataclass
class HeadPoseResult:
    angles: Optional[HeadPoseAngles]
    deviation_from_reference: Optional[HeadPoseAngles]
    has_reference: bool
    sustained_down_tilt: bool
    sustained_deviation: bool
