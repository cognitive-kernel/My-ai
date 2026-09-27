from __future__ import annotations

import time
from functools import lru_cache

from .config import settings
from .db import remember_knowledge
from .platform import hybrid_search, invalidate_hybrid_search_cache


@lru_cache(maxsize=128)
def _recall_cached(query: str, limit: int, bucket: int):
    return hybrid_search(query, limit)


def remember(topic, title, content, source_url=None):
    result = remember_knowledge(topic, title, content, source_url)
    _recall_cached.cache_clear()
    invalidate_hybrid_search_cache()
    return result


def recall(query, limit=8):
    limit = max(1, min(limit, 50))
    bucket = int(time.monotonic() // max(1, settings.cache_ttl_seconds))
    return _recall_cached(str(query).strip(), limit, bucket)
