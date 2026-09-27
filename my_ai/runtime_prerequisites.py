from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

def _requirements():
    if not PYPROJECT.is_file():
        return []
    try:
        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        return list(data.get("project", {}).get("dependencies", []))
    except (OSError, tomllib.TOMLDecodeError):
        return []

def _dist_name(spec):
    return re.split(r"[<>=!~;\[]", spec, maxsplit=1)[0].strip()

def _missing_python():
    missing = []
    for spec in _requirements():
        try:
            importlib.metadata.version(_dist_name(spec))
        except importlib.metadata.PackageNotFoundError:
            missing.append(spec)
    return missing

def _command_missing():
    names = ["git", "ffmpeg", "ffprobe"]
    if os.getenv("MYAI_CHECK_PENTEST_TOOLS", "true").lower() in {"1", "true", "yes"}:
        names.append("nmap")
    return [x for x in names if shutil.which(x) is None]

def _system_command(tool):
    if os.name == "nt":
        ids = {"git": "Git.Git", "ffmpeg": "Gyan.FFmpeg", "nmap": "Insecure.Nmap"}
        if shutil.which("winget") and tool in ids:
            return ["winget", "install", "--id", ids[tool], "-e", "--source", "winget", "--accept-package-agreements", "--accept-source-agreements"]
        if shutil.which("choco"):
            return ["choco", "install", {"git":"git","ffmpeg":"ffmpeg","nmap":"nmap"}[tool], "-y"]
        return None
    if sys.platform == "darwin" and shutil.which("brew"):
        return ["brew", "install", tool]
    for manager, command in (
        ("apt-get", ["sudo", "apt-get", "install", "-y", tool]),
        ("dnf", ["sudo", "dnf", "install", "-y", tool]),
        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", tool]),
    ):
        if shutil.which(manager):
            return command
    return None

def ensure_runtime_prerequisites(*, auto_install=True):
    result = {"python_missing": _missing_python(), "system_missing": _command_missing(),
              "installed_python": [], "installed_system": [], "errors": []}
    if not auto_install:
        return result
    if result["python_missing"]:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", *result["python_missing"]],
                           check=True, timeout=1800)
            result["installed_python"] = list(result["python_missing"])
        except Exception as exc:
            result["errors"].append(f"python: {exc}")
    for tool in list(result["system_missing"]):
        command = _system_command(tool)
        if not command:
            continue
        try:
            subprocess.run(command, check=True, timeout=1800)
            if shutil.which(tool):
                result["installed_system"].append(tool)
        except Exception as exc:
            result["errors"].append(f"{tool}: {exc}")
    result["python_missing"] = _missing_python()
    result["system_missing"] = _command_missing()
    return result

def startup_check():
    enabled = os.getenv("MYAI_AUTO_INSTALL_PREREQUISITES", "false").strip().lower() in {"1","true","yes","on"}
    return ensure_runtime_prerequisites(auto_install=enabled)


def _ollama_status() -> dict[str, object]:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=3) as response:
            return {"ok": response.status == 200, "url": base, "status": response.status}
    except Exception as exc:
        return {"ok": False, "url": base, "error": str(exc)}


def runtime_status() -> dict[str, object]:
    """Return a non-mutating readiness report for local end-to-end verification."""
    voice = {
        "whisper_binary": shutil.which("whisper-cli"),
        "piper_binary": shutil.which("piper"),
    }
    ollama = _ollama_status()
    missing_python = _missing_python()
    missing_system = _command_missing()
    checks = {
        "python_dependencies": not missing_python,
        "system_dependencies": not missing_system,
        "ollama": bool(ollama["ok"]),
        "voice_tools": bool(voice["whisper_binary"] and voice["piper_binary"]),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "python_missing": missing_python,
        "system_missing": missing_system,
        "ollama": ollama,
        "voice": voice,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "auto_install_enabled": os.getenv("MYAI_AUTO_INSTALL_PREREQUISITES", "false").strip().lower() in {"1","true","yes","on"},
    }
