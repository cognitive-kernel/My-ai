from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    expires_at: float | None
    version: str | None = None


class VersionedCache:
    """In-memory cache with TTL and explicit version invalidation."""

    def __init__(self) -> None:
        self._items: dict[str, CacheEntry] = {}

    @staticmethod
    def key(namespace: str, payload: Any, *, version: str | None = None) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        material = f"{namespace}|{version or ''}|{raw}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def set(self, key: str, value: Any, *, ttl: float | None = None, version: str | None = None) -> None:
        now = time.monotonic()
        self._items[key] = CacheEntry(value, now, now + ttl if ttl is not None else None, version)

    def get(self, key: str, *, version: str | None = None) -> Any | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and time.monotonic() >= entry.expires_at:
            self._items.pop(key, None)
            return None
        if version is not None and entry.version != version:
            return None
        return entry.value

    def invalidate(self, *, version: str | None = None) -> int:
        if version is None:
            count = len(self._items)
            self._items.clear()
            return count
        keys = [k for k, item in self._items.items() if item.version == version]
        for key in keys:
            self._items.pop(key, None)
        return len(keys)

    def clear_expired(self) -> int:
        now = time.monotonic()
        keys = [k for k, item in self._items.items() if item.expires_at is not None and now >= item.expires_at]
        for key in keys:
            self._items.pop(key, None)
        return len(keys)
