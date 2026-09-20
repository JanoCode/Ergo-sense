from dataclasses import dataclass
from typing import Optional
from enum import Enum

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
    pitch: float  # Inclinación arriba/abajo
    yaw: float    # Rotación izquierda/derecha
    roll: float   # Ladeado

@dataclass
class HeadPoseResult:
    angles: Optional[HeadPoseAngles]
    deviation_from_reference: Optional[HeadPoseAngles]
    has_reference: bool
    sustained_down_tilt: bool
    sustained_deviation: bool
