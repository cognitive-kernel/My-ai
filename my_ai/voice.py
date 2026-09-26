from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from .config import assert_write_allowed


def _whisper_binary() -> str | None:
    configured = os.getenv("WHISPER_CPP_BIN", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file() and (os.name == "nt" or path.stat().st_mode & 0o111):
            return str(path)
        raise RuntimeError("WHISPER_CPP_BIN must point to an executable file.")
    return shutil.which("whisper-cli")


def _piper_binary() -> str | None:
    return shutil.which("piper")


def status(transcription_model: str | None = None, synthesis_model: str | None = None) -> dict[str, object]:
    whisper = _whisper_binary()
    piper = _piper_binary()
    whisper_model_ok = bool(transcription_model and Path(transcription_model).expanduser().is_file())
    piper_model_ok = bool(synthesis_model and Path(synthesis_model).expanduser().is_file())
    return {
        "whisper_cpp": whisper,
        "piper": piper,
        "whisper_model": transcription_model,
        "piper_model": synthesis_model,
        "whisper_model_ready": whisper_model_ok,
        "piper_model_ready": piper_model_ok,
        "offline_ready": bool(whisper and piper and whisper_model_ok and piper_model_ok),
    }


def offline_roundtrip(
    audio_path: str,
    transcription_model: str,
    synthesis_model: str,
    output_path: str,
    language: str = "fa",
    text: str | None = None,
) -> dict[str, str]:
    """Run the complete local STT -> text -> TTS pipeline without a network service."""
    transcript = text if text is not None else transcribe(audio_path, transcription_model, language)
    if not transcript.strip():
        raise RuntimeError("Offline transcription returned empty text.")
    synthesized = synthesize(transcript, synthesis_model, output_path)
    return {"text": transcript, "audio_path": synthesized}


def transcribe(audio_path: str, model_path: str, language: str = "fa") -> str:
    binary = _whisper_binary()
    if not binary:
        raise RuntimeError("whisper.cpp executable was not found.")
    source = Path(audio_path).expanduser().resolve()
    model = Path(model_path).expanduser().resolve()
    if not source.is_file() or not model.is_file():
        raise FileNotFoundError("Audio input and Whisper model must both be existing files.")
    with tempfile.TemporaryDirectory(prefix="myai-whisper-") as temp:
        output_base = str(Path(temp) / "transcript")
        args = [binary, "-m", str(model), "-f", str(source), "-l", language, "-otxt", "-of", output_base]
        result = subprocess.run(args, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "whisper.cpp failed")
        output = Path(temp) / "transcript.txt"
        if output.exists():
            return output.read_text(encoding="utf-8").strip()
        return result.stdout.strip()


def synthesize(text: str, model_path: str, output_path: str) -> str:
    binary = _piper_binary()
    if not binary:
        raise RuntimeError("Piper executable was not found.")
    model = Path(model_path).expanduser().resolve()
    assert_write_allowed(output_path)
    output = Path(output_path).expanduser().resolve()
    if not model.is_file():
        raise FileNotFoundError("Piper model file not found.")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [binary, "--model", str(model), "--output_file", str(output)],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Piper failed")
    return str(output)
