from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import connect, init_db

ROOT = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT / "data" / ".settings_key"
SECRET_PREFIX = "enc:v1:"
SCHEMA = """CREATE TABLE IF NOT EXISTS app_settings (
 key TEXT PRIMARY KEY,
 value TEXT NOT NULL,
 secret INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);"""

def _key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        raw = KEY_PATH.read_bytes()
    else:
        raw = secrets.token_bytes(32)
        KEY_PATH.write_bytes(raw)
        try:
            os.chmod(KEY_PATH, 0o600)
        except OSError:
            pass
    if len(raw) != 32:
        raise RuntimeError("Invalid My-AI settings encryption key.")
    return raw

def _encrypt(value: str) -> str:
    nonce = os.urandom(12)
    data = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), b"my-ai-app-settings-v1")
    return SECRET_PREFIX + base64.b64encode(nonce + data).decode("ascii")

def _decrypt(value: str) -> str:
    if not value.startswith(SECRET_PREFIX):
        return value
    blob = base64.b64decode(value[len(SECRET_PREFIX):])
    if len(blob) < 13:
        raise ValueError("Invalid encrypted setting.")
    return AESGCM(_key()).decrypt(blob[:12], blob[12:], b"my-ai-app-settings-v1").decode("utf-8")

def ensure_schema() -> None:
    init_db()
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()

def get_setting(key: str, default: Any = None, *, secret: bool = False) -> Any:
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT value,secret FROM app_settings WHERE key=?", (key,)).fetchone()
    if not row:
        return default
    return _decrypt(str(row["value"])) if int(row["secret"]) else str(row["value"])

def set_setting(key: str, value: Any, *, secret: bool = False) -> None:
    ensure_schema()
    text = "" if value is None else str(value)
    stored = _encrypt(text) if secret and text else text
    with connect() as conn:
        conn.execute(
            """INSERT INTO app_settings(key,value,secret) VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,secret=excluded.secret,updated_at=CURRENT_TIMESTAMP""",
            (key, stored, 1 if secret else 0),
        )
        conn.commit()

def delete_setting(key: str) -> None:
    ensure_schema()
    with connect() as conn:
        conn.execute("DELETE FROM app_settings WHERE key=?", (key,))
        conn.commit()

def get_bool(key: str, default: bool = False) -> bool:
    return str(get_setting(key, "true" if default else "false")).strip().lower() in {"1","true","yes","on"}

def get_int(key: str, default: int) -> int:
    try:
        return int(get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default

def get_github_settings() -> dict[str, str]:
    return {
        "api_url": str(get_setting("github.api_url", "")),
        "repository": str(get_setting("github.repository", "")),
        "username": str(get_setting("github.username", "")),
        "token": str(get_setting("github.token", "", secret=True)),
    }
