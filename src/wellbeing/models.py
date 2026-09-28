from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class CycleState(Enum):
    WORKING = "WORKING"
    BREAK_DUE_SOON = "BREAK_DUE_SOON"
    BREAK_DUE = "BREAK_DUE"
    BREAKING = "BREAKING"

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
