from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any


class LocalFileError(ValueError):
    pass


APP_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = (APP_ROOT / "data" / "files").resolve()


def _roots() -> list[Path]:
    """Return readable filesystem roots without granting mutation rights."""
    if os.name == "nt":
        roots: list[Path] = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = Path(f"{letter}:\\")
            if path.exists():
                roots.append(path.resolve())
        return roots
    return [Path("/")]


def _safe_read_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(str(path))
    if not path.is_file():
        raise LocalFileError("Path is not a regular file.")
    return path


def inspect_file(value: str, *, max_hash_bytes: int = 16 * 1024 * 1024) -> dict[str, Any]:
    path = _safe_read_path(value)
    stat = path.stat()
    digest = None
    if stat.st_size <= max_hash_bytes:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        digest = h.hexdigest()
    return {
        "path": str(path),
        "name": path.name,
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "extension": path.suffix.lower(),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "sha256": digest,
        "read_only": True,
    }


def read_text(value: str, *, max_bytes: int = 4 * 1024 * 1024) -> str:
    path = _safe_read_path(value)
    if path.stat().st_size > max_bytes:
        raise LocalFileError(f"Text file exceeds the {max_bytes} byte read limit.")
    return path.read_text(encoding="utf-8", errors="replace")


def list_directory(value: str = "/") -> list[dict[str, Any]]:
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(str(path))
    result = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
        try:
            result.append({
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else None,
                "read_only": True,
            })
        except OSError:
            result.append({"name": child.name, "path": str(child), "is_dir": False, "size": None, "read_only": True, "error": "unreadable"})
    return result


def filesystem_roots() -> list[str]:
    return [str(p) for p in _roots()]


def workspace_path(filename: str) -> Path:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    candidate = (WORKSPACE_ROOT / Path(filename).name).resolve()
    candidate.relative_to(WORKSPACE_ROOT)
    return candidate
