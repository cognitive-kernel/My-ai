from __future__ import annotations

from pathlib import Path


HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def page() -> str:
    return HTML_PATH.read_text(encoding="utf-8")
