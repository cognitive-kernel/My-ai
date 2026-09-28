from contextvars import ContextVar
from typing import Any

_pending_attachments: ContextVar[list[dict[str, Any]]] = ContextVar("myai_pending_attachments", default=[])


def set_attachments(items: list[dict[str, Any]]) -> None:
    _pending_attachments.set(list(items or []))


def get_attachments() -> list[dict[str, Any]]:
    return list(_pending_attachments.get() or [])
