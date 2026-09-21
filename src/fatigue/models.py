from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

class FatigueLevel(Enum):
    NORMAL = "NORMAL"
    MILD = "MILD"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

@dataclass
class FatigueMetrics:
    """Métricas ya calculadas para una ventana de evaluación."""
    perclos: Optional[float] = None
    prolonged_closures: Optional[int] = None
    average_blink_duration: Optional[float] = None
    blink_rate: Optional[float] = None
    yawns_per_hour: Optional[float] = None
    yawns: Optional[int] = None
    average_yawn_duration: Optional[float] = None
    current_pitch_degrees: Optional[float] = None
    pitch_deviation_degrees: Optional[float] = None
    sustained_pitch_deviation: Optional[bool] = None
    sustained_head_drop: Optional[bool] = None
    session_duration_seconds: Optional[float] = None
    observation_duration_seconds: Optional[float] = None

@dataclass
class FatigueAssessment:
    timestamp: float
    score: float
    level: FatigueLevel
    confidence: float
    active_signals: List[str]
    unavailable_signals: List[str]
    reasons: List[str]

class FatigueEventType(Enum):
    PROLONGED_EYE_CLOSURE = "PROLONGED_EYE_CLOSURE"
    YAWN = "YAWN"
    HEAD_DROP = "HEAD_DROP"
    ENTERED_MODERATE = "ENTERED_MODERATE"
    ENTERED_HIGH = "ENTERED_HIGH"
    ENTERED_VERY_HIGH = "ENTERED_VERY_HIGH"

@dataclass
class StoredFatigueAssessment:
    session_id: int
    user_id: int
    timestamp: float
    score: float
    level: FatigueLevel
    confidence: float
    active_signals: List[str]
    unavailable_signals: List[str]
    reasons: List[str]
    perclos: Optional[float] = None
    head_deviation_degrees: Optional[float] = None
    id: Optional[int] = None

@dataclass
class FatigueEvent:
    session_id: int
    user_id: int
    event_type: FatigueEventType
    timestamp: float
    data: Dict[str, Any]
    id: Optional[int] = None

@dataclass
class SessionFatigueSummary:
    session_id: int
    user_id: int
    duration_seconds: int
    total_blinks: int
    average_blink_rate: Optional[float]
    average_blink_duration: Optional[float]
    average_perclos: Optional[float]
    max_perclos: Optional[float]
    prolonged_closures: int
    yawns: int
    max_head_deviation_degrees: Optional[float]
    average_score: Optional[float]
    max_score: Optional[float]
    max_level: Optional[FatigueLevel]
    time_to_mild_seconds: Optional[float]
    time_to_moderate_seconds: Optional[float]
    time_to_high_seconds: Optional[float]

@dataclass
class SessionFinalMetrics:
    duration_seconds: int
    total_blinks: int
    average_blink_rate: Optional[float]
    average_blink_duration: Optional[float]
    prolonged_closures: int
    yawns: int
    max_head_deviation_degrees: Optional[float] = None
