from __future__ import annotations
from ..memory import recall as _recall

def recall(query: str, limit: int = 8) -> list[dict]:
    return _recall(query, limit)
