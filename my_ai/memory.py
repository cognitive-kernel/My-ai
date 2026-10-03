from __future__ import annotations
import time
from functools import lru_cache
from .config import settings
from .db import execute, remember_knowledge
from .platform import hybrid_search, invalidate_hybrid_search_cache
def _memory_write_allowed(memory_type: str) -> None:
    from .settings_store import get_setting
    policy = str(get_setting(f"memory.{memory_type}_policy", "allow") or "allow").strip().lower()
    if policy == "deny":
        raise PermissionError(f"{memory_type} memory writes are denied by policy.")
    if policy == "approval":
        raise PermissionError(f"{memory_type} memory writes require explicit approval.")
    if policy != "allow":
        raise PermissionError(f"Unknown {memory_type} memory policy.")

@lru_cache(maxsize=128)
def _recall_cached(query: str, limit: int, bucket: int):
    return hybrid_search(query, limit, verified_only=True)
def remember(topic, title, content, source_url=None, *, product=None, version=None, validity_status="unknown", replaced_by_version=None, compatibility="unknown", memory_type="long_term"):
    _memory_write_allowed(str(memory_type))
    result = remember_knowledge(topic,title,content,source_url,product=product,version=version,validity_status=validity_status,replaced_by_version=replaced_by_version,compatibility=compatibility)
    _recall_cached.cache_clear(); invalidate_hybrid_search_cache(); return result
def delete_memory(knowledge_id: int) -> int:
    result = execute("DELETE FROM knowledge WHERE id=?", (int(knowledge_id),)); _recall_cached.cache_clear(); invalidate_hybrid_search_cache(); return result
forget = delete_memory
clear_memory = delete_memory
def recall(query, limit=8):
    limit=max(1,min(limit,50)); bucket=int(time.monotonic()//max(1,settings.cache_ttl_seconds)); return _recall_cached(str(query).strip(),limit,bucket)
