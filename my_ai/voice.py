from __future__ import annotations

import shutil
import os
import subprocess
from pathlib import Path


def _whisper_binary() -> str | None:
    configured=os.getenv("WHISPER_CPP_BIN","").strip()
    if configured:
        path=Path(configured).expanduser().resolve()
        if path.is_file() and (os.name == "nt" or path.stat().st_mode & 0o111):
            return str(path)
        raise RuntimeError("WHISPER_CPP_BIN must point to an executable file.")
    return shutil.which("whisper-cli")


def _piper_binary() -> str | None:
    return shutil.which("piper")


def status() -> dict[str, object]:
    whisper = _whisper_binary()
    piper = _piper_binary()
    return {"whisper_cpp": whisper, "piper": piper, "offline_ready": bool(whisper and piper)}


def transcribe(audio_path: str, model_path: str, language: str = "fa") -> str:
    binary = _whisper_binary()
    if not binary:
        raise RuntimeError("whisper.cpp executable was not found.")
    args = [binary, "-m", model_path, "-f", audio_path, "-l", language, "-otxt"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "whisper.cpp failed")
    output = Path(audio_path).with_suffix(".txt")
    return output.read_text(encoding="utf-8").strip() if output.exists() else result.stdout.strip()


def synthesize(text: str, model_path: str, output_path: str) -> str:
    binary = _piper_binary()
    if not binary:
        raise RuntimeError("Piper executable was not found.")
    result = subprocess.run([binary, "--model", model_path, "--output_file", output_path], input=text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Piper failed")
    return output_path
