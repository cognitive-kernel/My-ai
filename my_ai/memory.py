from __future__ import annotations

import time
from functools import lru_cache

from .config import settings
from .db import execute, remember_knowledge
from .platform import hybrid_search, invalidate_hybrid_search_cache


@lru_cache(maxsize=128)
def _recall_cached(query: str, limit: int, bucket: int):
    return hybrid_search(query, limit, verified_only=True)


def remember(topic, title, content, source_url=None, *, product=None, version=None, validity_status="unknown", replaced_by_version=None, compatibility="unknown"):
    result = remember_knowledge(
        topic,
        title,
        content,
        source_url,
        product=product,
        version=version,
        validity_status=validity_status,
        replaced_by_version=replaced_by_version,
        compatibility=compatibility,
    )
    _recall_cached.cache_clear()
    invalidate_hybrid_search_cache()
    return result


def delete_memory(knowledge_id: int) -> int:
    """Delete one persisted knowledge item and invalidate retrieval caches."""
    result = execute("DELETE FROM knowledge WHERE id=?", (int(knowledge_id),))
    _recall_cached.cache_clear()
    invalidate_hybrid_search_cache()
    return result


def recall(query, limit=8):
    limit = max(1, min(limit, 50))
    bucket = int(time.monotonic() // max(1, settings.cache_ttl_seconds))
    return _recall_cached(str(query).strip(), limit, bucket)


forget = delete_memory
clear_memory = delete_memory
