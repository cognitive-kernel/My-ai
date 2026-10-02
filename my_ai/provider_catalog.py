from __future__ import annotations

import json
import time
from typing import Any

from .access_policy import assert_mutation_allowed
from .db import connect
from .settings_store import _decrypt, _encrypt


SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    protocol TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    auth_type TEXT NOT NULL DEFAULT 'none',
    auth_secret TEXT NOT NULL DEFAULT '',
    capabilities_json TEXT NOT NULL DEFAULT '{}',
    version TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    timeout_seconds REAL NOT NULL DEFAULT 30,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_provider_keys (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 provider_id INTEGER NOT NULL,
 key_name TEXT NOT NULL,
 secret TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1,
 priority INTEGER NOT NULL DEFAULT 100,
 created_at REAL NOT NULL,
 last_used_at REAL,
 UNIQUE(provider_id,key_name),
 FOREIGN KEY(provider_id) REFERENCES llm_providers(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS llm_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL REFERENCES llm_providers(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    tasks_json TEXT NOT NULL DEFAULT '[]',
    context_length INTEGER,
    limits_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 100,
    enabled INTEGER NOT NULL DEFAULT 1,
    version TEXT NOT NULL DEFAULT '',
    UNIQUE(provider_id, model_id)
);
"""


def ensure_schema() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _row(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["capabilities"] = json.loads(item.pop("capabilities_json") or "{}")
    item["enabled"] = bool(item["enabled"])
    item["auth_configured"] = bool(item.pop("auth_secret", ""))
    return item


def add_provider_key(provider_id: int, key_name: str, secret: str, *, priority: int = 100, active: bool = True) -> dict[str, Any]:
    assert_mutation_allowed(f"llm-provider-key:{provider_id}:{key_name}")
    ensure_schema()
    if not key_name.strip() or not secret: raise ValueError("key name and secret are required")
    now=time.time()
    with connect() as conn:
        conn.execute("""INSERT INTO llm_provider_keys(provider_id,key_name,secret,active,priority,created_at)
                        VALUES(?,?,?,?,?,?) ON CONFLICT(provider_id,key_name) DO UPDATE SET
                        secret=excluded.secret,active=excluded.active,priority=excluded.priority""",
                     (int(provider_id),key_name.strip(),_encrypt(secret),int(active),int(priority),now))
        conn.commit()
    return {"provider_id":provider_id,"key_name":key_name,"active":active,"priority":priority}

def list_provider_keys(provider_id: int) -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as conn:
        rows=conn.execute("SELECT id,provider_id,key_name,active,priority,created_at,last_used_at FROM llm_provider_keys WHERE provider_id=? ORDER BY priority,id",(int(provider_id),)).fetchall()
    return [dict(r)|{"active":bool(r["active"])} for r in rows]

def rotate_provider_key(provider_id: int) -> dict[str, Any]:
    ensure_schema()
    with connect() as conn:
        row=conn.execute("SELECT id,key_name FROM llm_provider_keys WHERE provider_id=? AND active=1 ORDER BY priority,id LIMIT 1",(int(provider_id),)).fetchone()
        if not row: raise ValueError("no active provider key")
        conn.execute("UPDATE llm_provider_keys SET active=0 WHERE provider_id=?",(int(provider_id),))
        conn.execute("UPDATE llm_provider_keys SET active=1,last_used_at=? WHERE id=?",(time.time(),int(row["id"])))
        conn.commit()
    return {"provider_id":provider_id,"active_key":row["key_name"]}

def list_providers(*, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,name,protocol,endpoint,auth_type,auth_secret,capabilities_json,version,enabled,timeout_seconds,created_at,updated_at FROM llm_providers"
            + ("" if include_disabled else " WHERE enabled=1")
            + " ORDER BY name"
        ).fetchall()
    return [_row(row) for row in rows]


def upsert_provider(
    *,
    name: str,
    protocol: str,
    endpoint: str,
    auth_type: str = "none",
    secret: str = "",
    capabilities: dict[str, Any] | None = None,
    version: str = "",
    timeout_seconds: float = 30,
    enabled: bool = True,
) -> dict[str, Any]:
    assert_mutation_allowed(f"llm-provider:{name}")
    name, protocol, endpoint = name.strip(), protocol.strip(), endpoint.strip()
    if not name or not protocol or not endpoint:
        raise ValueError("provider name, protocol and endpoint are required")
    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        raise ValueError("provider endpoint must use http:// or https://")
    if timeout_seconds <= 0:
        raise ValueError("provider timeout must be positive")
    ensure_schema()
    now = time.time()
    encrypted = _encrypt(secret) if secret else ""
    with connect() as conn:
        conn.execute(
            """INSERT INTO llm_providers(name,protocol,endpoint,auth_type,auth_secret,capabilities_json,version,enabled,timeout_seconds,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(name) DO UPDATE SET protocol=excluded.protocol,endpoint=excluded.endpoint,
               auth_type=excluded.auth_type,auth_secret=CASE WHEN excluded.auth_secret='' THEN llm_providers.auth_secret ELSE excluded.auth_secret END,
               capabilities_json=excluded.capabilities_json,version=excluded.version,enabled=excluded.enabled,
               timeout_seconds=excluded.timeout_seconds,updated_at=excluded.updated_at""",
            (name, protocol, endpoint, auth_type, encrypted, json.dumps(capabilities or {}, ensure_ascii=False), version, int(enabled), timeout_seconds, now, now),
        )
        row = conn.execute("SELECT * FROM llm_providers WHERE name=?", (name,)).fetchone()
        conn.commit()
    return _row(row)


def delete_model(provider_id: int, model_id: str) -> None:
    assert_mutation_allowed(f"llm-model-delete:{provider_id}:{model_id}")
    ensure_schema()
    with connect() as conn:
        conn.execute("DELETE FROM llm_models WHERE provider_id=? AND model_id=?", (int(provider_id), str(model_id).strip()))
        conn.commit()


def delete_provider(provider_id: int) -> None:
    assert_mutation_allowed(f"llm-provider-delete:{provider_id}")
    ensure_schema()
    with connect() as conn:
        conn.execute("DELETE FROM llm_providers WHERE id=?", (int(provider_id),))
        conn.commit()


def upsert_model(
    *,
    provider_id: int,
    model_id: str,
    tasks: list[str] | None = None,
    context_length: int | None = None,
    limits: dict[str, Any] | None = None,
    priority: int = 100,
    version: str = "",
    enabled: bool = True,
) -> dict[str, Any]:
    assert_mutation_allowed(f"llm-model:{provider_id}:{model_id}")
    if not model_id.strip() or priority < 0 or (context_length is not None and context_length <= 0):
        raise ValueError("invalid model catalog metadata")
    ensure_schema()
    with connect() as conn:
        conn.execute(
            """INSERT INTO llm_models(provider_id,model_id,tasks_json,context_length,limits_json,priority,enabled,version)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(provider_id,model_id) DO UPDATE SET tasks_json=excluded.tasks_json,context_length=excluded.context_length,
               limits_json=excluded.limits_json,priority=excluded.priority,enabled=excluded.enabled,version=excluded.version""",
            (provider_id, model_id.strip(), json.dumps(tasks or [], ensure_ascii=False), context_length, json.dumps(limits or {}, ensure_ascii=False), priority, int(enabled), version),
        )
        row = conn.execute("SELECT * FROM llm_models WHERE provider_id=? AND model_id=?", (provider_id, model_id.strip())).fetchone()
        conn.commit()
    item = dict(row)
    item["tasks"] = json.loads(item.pop("tasks_json") or "[]")
    item["limits"] = json.loads(item.pop("limits_json") or "{}")
    item["enabled"] = bool(item["enabled"])
    return item


def list_models(*, provider_id: int | None = None, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_schema()
    clauses, params = [], []
    if provider_id is not None:
        clauses.append("provider_id=?")
        params.append(int(provider_id))
    if not include_disabled:
        clauses.append("enabled=1")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM llm_models" + where + " ORDER BY priority, model_id", params).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["tasks"] = json.loads(item.pop("tasks_json") or "[]")
        item["limits"] = json.loads(item.pop("limits_json") or "{}")
        item["enabled"] = bool(item["enabled"])
        items.append(item)
    return items


def get_provider_runtime_config(provider_id: int) -> dict[str, Any]:
    """Return decrypted runtime configuration only at the adapter boundary."""
    ensure_schema()
    with connect() as conn:
        provider = conn.execute("SELECT * FROM llm_providers WHERE id=?", (int(provider_id),)).fetchone()
        if not provider: raise KeyError(f"Unknown provider id: {provider_id}")
        key = conn.execute("SELECT key_name,secret FROM llm_provider_keys WHERE provider_id=? AND active=1 ORDER BY priority,id LIMIT 1", (int(provider_id),)).fetchone()
    if key: secret, key_name = _decrypt(str(key["secret"])), str(key["key_name"])
    else: secret, key_name = (_decrypt(str(provider["auth_secret"])) if provider["auth_secret"] else ""), ""
    return {
        "id": int(provider["id"]), "name": str(provider["name"]), "protocol": str(provider["protocol"]),
        "endpoint": str(provider["endpoint"]), "auth_type": str(provider["auth_type"]),
        "api_key": secret, "key_name": key_name,
        "capabilities": json.loads(provider["capabilities_json"] or "{}"),
        "version": str(provider["version"] or ""), "timeout_seconds": float(provider["timeout_seconds"] or 30),
        "enabled": bool(provider["enabled"]),
    }

def import_catalog(payload: dict[str, Any]) -> dict[str, int]:
    """Import provider/model metadata while preserving existing secrets."""
    if not isinstance(payload, dict) or int(payload.get("version", 0)) != 1: raise ValueError("Unsupported catalog version.")
    imported = {"providers": 0, "models": 0}; provider_ids: dict[str, int] = {}
    for item in payload.get('providers', []):
        current = upsert_provider(name=str(item['name']), protocol=str(item['protocol']), endpoint=str(item['endpoint']), auth_type=str(item.get('auth_type','none')), capabilities=dict(item.get('capabilities') or {}), version=str(item.get('version','')), timeout_seconds=float(item.get('timeout_seconds',30)), enabled=bool(item.get('enabled',True)))
        provider_ids[str(item['name'])] = int(current['id']); imported['providers'] += 1
    for item in payload.get('models', []):
        pid = provider_ids.get(str(item.get('provider_name','')), int(item.get('provider_id',0)))
        if pid <= 0: raise ValueError("Model record references an unknown provider.")
        upsert_model(provider_id=pid, model_id=str(item['model_id']), tasks=list(item.get('tasks') or []), context_length=item.get('context_length'), limits=dict(item.get('limits') or {}), priority=int(item.get('priority',100)), version=str(item.get('version','')), enabled=bool(item.get('enabled',True)))
        imported['models'] += 1
    return imported

def export_catalog() -> dict[str, Any]:
    providers = list_providers()
    with connect() as conn:
        models = [dict(row) for row in conn.execute("SELECT * FROM llm_models ORDER BY id").fetchall()]
    for item in providers:
        item.pop("auth_configured", None)
        item.pop("created_at", None)
        item.pop("updated_at", None)
    for item in models:
        item["tasks"] = json.loads(item.pop("tasks_json") or "[]")
        item["limits"] = json.loads(item.pop("limits_json") or "{}")
        provider = next((p for p in providers if int(p["id"]) == int(item["provider_id"])), None)
        item["provider_name"] = provider["name"] if provider else ""
    return {"version": 1, "providers": providers, "models": models}
