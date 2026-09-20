from __future__ import annotations

from .db import remember_knowledge, search_knowledge


def remember(topic, title, content, source_url=None):
    """Store knowledge once by normalized content and return the canonical row id."""
    return remember_knowledge(topic, title, content, source_url)


def recall(query, limit=8):
    return search_knowledge(query, max(1, min(limit, 50)))
