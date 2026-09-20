from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    name: str
    id: Optional[int] = None
    created_at: Optional[str] = None
