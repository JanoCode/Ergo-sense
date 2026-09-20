from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Session:
    user_id: int
    id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
