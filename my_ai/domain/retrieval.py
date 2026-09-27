from __future__ import annotations
from .__init__ import __doc__ as _domain_marker
from ..memory import recall as _recall

def recall(query: str, limit: int = 8) -> list[dict]:
    return _recall(query, limit)
