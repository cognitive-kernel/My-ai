from __future__ import annotations
import time
from functools import lru_cache
from .config import settings
from .control_plane import get_record
from .db import execute, remember_knowledge
from .platform import hybrid_search, invalidate_hybrid_search_cache

_MEMORY_TYPES = {"short_term", "long_term", "experiential"}


def _memory_policy(memory_type: str) -> dict:
    normalized = str(memory_type or "long_term").strip().lower()
    if normalized not in _MEMORY_TYPES:
        raise ValueError(f"unsupported memory type: {memory_type}")
    record = get_record("memory.policy", normalized)
    policy = dict(record.get("payload") or {}) if record and record.get("enabled") else {}
    policy.setdefault("allow_write", True)
    policy.setdefault("allow_recall", True)
    policy.setdefault("scope", normalized)
    policy.setdefault("retention_days", 365)
    return policy


@lru_cache(maxsize=128)
def _recall_cached(query: str, limit: int, bucket: int):
    return hybrid_search(query, limit, verified_only=True)


def remember(topic, title, content, source_url=None, *, product=None, version=None, validity_status="unknown", replaced_by_version=None, compatibility="unknown", memory_type="long_term"):
    policy = _memory_policy(memory_type)
    if not policy["allow_write"]:
        raise PermissionError(f"memory write denied by policy: {memory_type}")
    result = remember_knowledge(topic, title, content, source_url, product=product, version=version, validity_status=validity_status, replaced_by_version=replaced_by_version, compatibility=compatibility)
    _recall_cached.cache_clear(); invalidate_hybrid_search_cache(); return result


def delete_memory(knowledge_id: int) -> int:
    result = execute("DELETE FROM knowledge WHERE id=?", (int(knowledge_id),)); _recall_cached.cache_clear(); invalidate_hybrid_search_cache(); return result

forget = delete_memory
clear_memory = delete_memory


def recall(query, limit=8, *, memory_type="long_term"):
    policy = _memory_policy(memory_type)
    if not policy["allow_recall"]:
        return []
    limit=max(1,min(limit,50)); bucket=int(time.monotonic()//max(1,settings.cache_ttl_seconds)); return _recall_cached(str(query).strip(),limit,bucket)


def memory_policies() -> dict[str, dict]:
    return {kind: _memory_policy(kind) for kind in sorted(_MEMORY_TYPES)}
