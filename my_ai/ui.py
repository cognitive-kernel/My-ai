from __future__ import annotations

from pathlib import Path


HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def page() -> str:
    """Return the canonical chat UI without injecting a second chat runtime.

    The static page owns session state, history loading, send/rename/pin/delete
    handlers, and initialization. A second injected runtime caused two competing
    session states and replaced the chat rows without action buttons.
    """
    return HTML_PATH.read_text(encoding="utf-8")


HTML = page()
