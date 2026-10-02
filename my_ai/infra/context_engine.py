from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ContextItem:
    text: str
    source: str = ""
    priority: float = 0.0
    tokens: int | None = None


def assemble_context(
    items: Iterable[ContextItem],
    *,
    max_chars: int = 20000,
    required_sources: set[str] | None = None,
) -> list[ContextItem]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    ordered = sorted(items, key=lambda item: (-item.priority, item.source, item.text))
    result: list[ContextItem] = []
    used = 0
    required = set(required_sources or ())
    for item in ordered:
        size = len(item.text)
        if item.source in required or used + size <= max_chars:
            result.append(item)
            used += size
    return result


def render_context(items: Iterable[ContextItem]) -> str:
    return "

".join(
        f"[source={item.source or 'unknown'} priority={item.priority:g}]
{item.text}"
        for item in items
    )
