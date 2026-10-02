from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable
import time
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    trace_id: str | None = None


class EventBus:
    """Small in-process event bus with deterministic subscription order."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Event], Any]]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, name: str, handler: Callable[[Event], Any]) -> None:
        if not name.strip() or not callable(handler):
            raise ValueError("event name and callable handler are required")
        with self._lock:
            if handler not in self._handlers[name]:
                self._handlers[name].append(handler)

    def unsubscribe(self, name: str, handler: Callable[[Event], Any]) -> None:
        with self._lock:
            if name in self._handlers and handler in self._handlers[name]:
                self._handlers[name].remove(handler)

    def publish(self, name: str, payload: dict[str, Any] | None = None, *, trace_id: str | None = None) -> Event:
        event = Event(name=name, payload=dict(payload or {}), trace_id=trace_id)
        with self._lock:
            handlers = list(self._handlers.get(name, ())) + list(self._handlers.get("*", ()))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("event handler failed", extra={"event": name, "trace_id": trace_id})
        return event
