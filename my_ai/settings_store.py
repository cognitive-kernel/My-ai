from __future__ import annotations

import base64
import logging
import os
import secrets
from pathlib import Path
from typing import Any
SETTING_REGISTRY: dict[str, dict[str, Any]] = {
    "logging.level": {"type":"enum","default":"WARNING","choices":["DEBUG","INFO","WARNING","ERROR","CRITICAL"],"description":"Minimum console log level."},
    "learning.interval_seconds": {"type":"int","default":3600,"min":60,"max":86400,"description":"Learning interval in seconds."},
    "learning.max_retries": {"type":"int","default":5,"min":1,"max":20,"description":"Maximum learning retries."},
    "resources.cpu_percent": {"type":"float","default":70.0,"min":1.0,"max":100.0,"description":"Maximum CPU percentage."},
    "resources.cpu_threads": {"type":"int","default":8,"min":1,"max":128,"description":"Maximum CPU threads."},
    "resources.ram_percent": {"type":"float","default":80.0,"min":1.0,"max":100.0,"description":"Maximum RAM percentage."},
    "resources.gpu_layers": {"type":"int","default":0,"min":0,"max":128,"description":"GPU layers."},
}

def get_setting_registry() -> dict[str, dict[str, Any]]:
    return {k: dict(v) for k, v in SETTING_REGISTRY.items()}

def validate_registered_setting(key: str, value: Any) -> Any:
    meta = SETTING_REGISTRY.get(key)
    if not meta: raise KeyError(f"Unknown registered setting: {key}")
    kind = meta["type"]
    if kind == "int":
        try: value = int(value)
        except (TypeError, ValueError) as exc: raise ValueError(f"{key} must be integer") from exc
    elif kind == "float":
        try: value = float(value)
        except (TypeError, ValueError) as exc: raise ValueError(f"{key} must be number") from exc
    else: value = str(value)
    if "min" in meta and value < meta["min"]: raise ValueError(f"{key} below minimum")
    if "max" in meta and value > meta["max"]: raise ValueError(f"{key} above maximum")
    if "choices" in meta and value not in meta["choices"]: raise ValueError(f"{key} has invalid choice")
    return value

def reset_setting(key: str) -> Any:
    meta = SETTING_REGISTRY.get(key)
    if not meta: raise KeyError(f"Unknown registered setting: {key}")
    delete_setting(key)
    return meta["default"]


from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import connect
from .access_policy import assert_mutation_allowed

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
        except OSError as exc:
            logging.getLogger(__name__).debug("settings key chmod failed: %s", exc)
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
    # Settings access is on a hot path, including the learning scheduler.
    # Do not run the full DB migration on every read: init_db() performs
    # multiple writes and can contend with learning/background transactions.
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
    assert_mutation_allowed(f"setting:{key}")
    ensure_schema()
    if key in SETTING_REGISTRY:
        value = validate_registered_setting(key, value)\n    text = "" if value is None else str(value)
    stored = _encrypt(text) if secret and text else text
    with connect() as conn:
        conn.execute(
            """INSERT INTO app_settings(key,value,secret) VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,secret=excluded.secret,updated_at=CURRENT_TIMESTAMP""",
            (key, stored, 1 if secret else 0),
        )
        conn.commit()

def delete_setting(key: str) -> None:
    assert_mutation_allowed(f"setting-delete:{key}")
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
