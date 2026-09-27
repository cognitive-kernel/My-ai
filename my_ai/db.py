"""Compatibility facade; persistence implementation lives in my_ai.infra.persistence."""
from __future__ import annotations

import importlib
import sys

if "my_ai.infra.persistence" in sys.modules:
    _persistence = importlib.reload(sys.modules["my_ai.infra.persistence"])
else:
    _persistence = importlib.import_module("my_ai.infra.persistence")

settings = _persistence.settings
SCHEMA = _persistence.SCHEMA
connect = _persistence.connect
execute = _persistence.execute
fetch_all = _persistence.fetch_all
_write_blocked = _persistence._write_blocked
init_db = _persistence.init_db
_normalize_search_text = _persistence._normalize_search_text
def remember_knowledge(*args, **kwargs):
    _persistence.connect = connect
    return _persistence.remember_knowledge(*args, **kwargs)


def search_knowledge(*args, **kwargs):
    _persistence.connect = connect
    return _persistence.search_knowledge(*args, **kwargs)

__all__ = ["SCHEMA", "connect", "execute", "fetch_all", "init_db", "_normalize_search_text", "remember_knowledge", "search_knowledge"]
