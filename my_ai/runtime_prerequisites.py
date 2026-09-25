from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"

def _requirements():
    if not REQUIREMENTS.is_file():
        return []
    return [x.strip() for x in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.lstrip().startswith(("#", "-"))]

def _dist_name(spec):
    return re.split(r"[<>=!~;\[]", spec, 1)[0].strip()

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
            return ["winget", "install", "--id", ids[tool], "-e", "--accept-package-agreements", "--accept-source-agreements"]
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
    enabled = os.getenv("MYAI_AUTO_INSTALL_PREREQUISITES", "true").strip().lower() in {"1","true","yes","on"}
    return ensure_runtime_prerequisites(auto_install=enabled)
