from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CycleState(Enum):
    WORKING = "WORKING"
    BREAK_DUE_SOON = "BREAK_DUE_SOON"
    BREAK_DUE = "BREAK_DUE"
    BREAKING = "BREAKING"


class BreakEventType(Enum):
    BREAK_STARTED = "BREAK_STARTED"
    BREAK_POSTPONED = "BREAK_POSTPONED"


class BreakCompletionType(Enum):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"


@dataclass
class WellbeingSessionState:
    session_id: int
    session_started_at: datetime
    continuous_usage_started_at: datetime
    session_elapsed_seconds: int = 0
    continuous_usage_seconds: int = 0
    last_break_at: Optional[datetime] = None
    completed_breaks: int = 0
    postponed_breaks: int = 0


@dataclass
class BreakEvent:
    session_id: int
    user_id: int
    event_type: BreakEventType
    timestamp: Optional[datetime] = None
    postpone_duration_minutes: Optional[int] = None
    id: Optional[int] = None


@dataclass
class WellbeingBreak:
    session_id: int
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    completion_type: Optional[BreakCompletionType] = None
    id: Optional[int] = None
