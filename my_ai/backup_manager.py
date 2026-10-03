"""Configuration-driven database backup/restore primitives."""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from .config import settings
from .backup_crypto import MAGIC, decrypt_file, encrypt_file
from .settings_store import get_setting

DB_PATH = settings.db_path


def _encryption_password() -> str | None:
    mode = str(get_setting("database.backup.encryption", "none") or "none").strip().lower()
    if mode in {"none", "off", "disabled"}:
        return None
    if mode != "aes-gcm":
        raise ValueError(f"Unsupported backup encryption policy: {mode}")
    password = str(get_setting("database.backup.encryption_password", "") or "")
    if len(password) < 12:
        raise ValueError("Backup encryption password must contain at least 12 characters.")
    return password


def backup(destination: str, *, overwrite: bool = False, password: str | None = None) -> dict:
    src = Path(DB_PATH)
    dst = Path(destination)
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        raise FileExistsError(dst)

    encryption_password = password if password is not None else _encryption_password()
    if encryption_password:
        plain = dst.with_name(f".{dst.name}.plain-{os.getpid()}-{time.time_ns()}")
        encrypted = dst.with_name(f".{dst.name}.encrypted-{os.getpid()}-{time.time_ns()}")
        try:
            shutil.copy2(src, plain)
            encrypt_file(plain, encrypted, encryption_password)
            os.replace(encrypted, dst)
        finally:
            plain.unlink(missing_ok=True)
            encrypted.unlink(missing_ok=True)
    else:
        shutil.copy2(src, dst)

    return {
        "path": str(dst),
        "size": dst.stat().st_size,
        "created_at": time.time(),
        "encrypted": bool(encryption_password),
    }


def restore(source: str, *, target: str | None = None, password: str | None = None) -> dict:
    src = Path(source)
    dst = Path(target or DB_PATH)
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)

    encryption_password = password if password is not None else _encryption_password()
    blob = src.read_bytes()
    is_encrypted = blob.startswith(MAGIC)
    if is_encrypted and not encryption_password:
        raise ValueError("Encrypted backup requires the configured encryption password.")
    if encryption_password and not is_encrypted:
        raise ValueError("Configured encrypted restore requires an encrypted backup.")

    tmp = dst.with_suffix(dst.suffix + ".restore.tmp")
    try:
        if is_encrypted:
            try:
                decrypt_file(src, tmp, encryption_password)
            except Exception as exc:
                raise ValueError("Unable to decrypt encrypted backup.") from exc
        else:
            shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "path": str(dst),
        "size": dst.stat().st_size,
        "restored_at": time.time(),
        "encrypted": is_encrypted,
    }


def prune_backups(destination: str, retention: int) -> list[str]:
    directory = Path(destination)
    if not directory.exists():
        return []
    files = sorted(
        (p for p in directory.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed: list[str] = []
    for path in files[max(1, retention):]:
        path.unlink()
        removed.append(str(path))
    return removed
