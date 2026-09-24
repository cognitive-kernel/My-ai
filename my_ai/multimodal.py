from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .file_processing import detect_type, extract_text, generic_inspection
from .local_files import inspect_file
from .voice import transcribe


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


def _ffmpeg_extract_audio(source: Path, destination: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required for media transcription.")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(destination)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FFmpeg audio extraction failed.")


def _video_frames(source: Path, directory: Path, count: int = 4) -> list[Path]:
    if not shutil.which("ffmpeg"):
        return []
    pattern = directory / "frame-%02d.jpg"
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vf", f"fps=1/{max(1, 30 // max(1, count))}", "-frames:v", str(count), str(pattern)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode:
        return []
    return sorted(directory.glob("frame-*.jpg"))[:count]


def _ollama_vision(path: Path, prompt: str) -> str:
    raw = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime.startswith("image/"):
        raise ValueError("Vision analysis requires an image input.")
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


def _transcribe_media(path: Path, kind: str) -> dict[str, Any]:
    model_path = os.getenv("WHISPER_MODEL_PATH", "").strip()
    language = os.getenv("WHISPER_LANGUAGE", "fa").strip() or "fa"
    if not model_path:
        return {"status": "not_configured", "message": "Set WHISPER_MODEL_PATH to enable local speech transcription."}
    model = Path(model_path).expanduser().resolve()
    if not model.is_file():
        return {"status": "error", "message": "WHISPER_MODEL_PATH does not point to an existing model file."}
    with tempfile.TemporaryDirectory(prefix="myai-media-") as temp:
        audio = Path(temp) / "audio.wav"
        source = path
        if kind == "video":
            _ffmpeg_extract_audio(path, audio)
            source = audio
        try:
            text = transcribe(str(source), str(model), language)
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
    return {"status": "ok", "language": language, "text": text}


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
        result["transcription"] = _transcribe_media(target, kind)
        if kind == "video":
            with tempfile.TemporaryDirectory(prefix="myai-video-frames-") as temp:
                frames = _video_frames(target, Path(temp))
                frame_results = []
                for frame in frames:
                    try:
                        frame_results.append(_ollama_vision(frame, "Describe this video frame and identify important visible content."))
                    except Exception as exc:
                        frame_results.append(f"frame analysis error: {exc}")
                result["frame_analysis"] = frame_results
    else:
        result["generic"] = generic_inspection(str(target))
        result["message"] = "Generic metadata, hash, and archive inspection completed; no unsafe execution is performed for unknown file types."
    return result
