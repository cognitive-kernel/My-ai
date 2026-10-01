from __future__ import annotations

import time
from functools import lru_cache

from .config import settings
from .db import remember_knowledge
from .platform import hybrid_search, invalidate_hybrid_search_cache

MEMORY_CATEGORIES = frozenset({
    "user_preferences",
    "project_facts",
    "technical_decisions",
    "lessons_learned",
    "research_evidence",
    "known_failures",
    "successful_patterns",
    "temporary_context",
})


@lru_cache(maxsize=128)
def _recall_cached(query: str, limit: int, bucket: int):
    return hybrid_search(query, limit, verified_only=True)


def remember(topic, title, content, source_url=None, category="project_facts"):
    category = str(category or "project_facts").strip().lower()
    if category not in MEMORY_CATEGORIES:
        raise ValueError(f"Unsupported memory category: {category}")
    result = remember_knowledge(topic, title, content, source_url, category)
    _recall_cached.cache_clear()
    invalidate_hybrid_search_cache()
    return result


def recall(query, limit=8):
    # Direct DB mutations are a supported maintenance/test path, so invalidate the
    # lower-level retrieval cache before reading rather than returning stale knowledge.
    invalidate_hybrid_search_cache()
    limit = max(1, min(limit, 50))
    bucket = int(time.monotonic() // max(1, settings.cache_ttl_seconds))
    return _recall_cached(str(query).strip(), limit, bucket)
