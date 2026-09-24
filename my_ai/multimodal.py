from __future__ import annotations

import base64
import json
import mimetypes
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .file_processing import detect_type, extract_text
from .local_files import inspect_file


def _ffprobe(path: Path) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _ollama_vision(path: Path, prompt: str) -> str:
    raw = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime.startswith("image/"):
        raise ValueError("Vision analysis currently requires an image input.")
    payload = {
        "model": getattr(settings, "ollama_model", "qwen2.5:7b"),
        "stream": False,
        "messages": [{"role": "user", "content": prompt, "images": [raw]}],
    }
    response = httpx.post(
        f"{getattr(settings, 'ollama_base_url', 'http://127.0.0.1:11434').rstrip('/')}/api/chat",
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    return str(data["message"]["content"])


def analyze(path: str, prompt: str = "Analyze this file and describe useful findings.") -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    info = inspect_file(str(target))
    kind = detect_type(str(target))["kind"]
    result: dict[str, Any] = {"file": info, "kind": kind}
    if kind == "image":
        try:
            from PIL import Image
            with Image.open(target) as image:
                result["metadata"] = {"format": image.format, "mode": image.mode, "width": image.width, "height": image.height}
        except Exception as exc:
            result["metadata_error"] = str(exc)
        try:
            result["analysis"] = _ollama_vision(target, prompt)
        except Exception as exc:
            result["analysis_error"] = str(exc)
    elif kind in {"text", "document", "spreadsheet", "pdf"}:
        result["content"] = extract_text(str(target))
    elif kind in {"audio", "video"}:
        result["media"] = _ffprobe(target)
        result["analysis"] = "Media metadata extracted locally. Speech/transcription can be requested with the configured voice model."
    else:
        result["message"] = "The file was inspected safely; no specialized local analyzer is registered for this type yet."
    return result
