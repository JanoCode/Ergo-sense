from dataclasses import dataclass
from typing import Optional

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
