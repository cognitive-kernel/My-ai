from __future__ import annotations

import json
import time
from typing import Any

from .access_policy import assert_mutation_allowed
def _connect():
    from .db import connect
    return connect()
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
CREATE TABLE IF NOT EXISTS llm_routing_rules (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 task TEXT NOT NULL UNIQUE,
 model_id TEXT NOT NULL,
 provider_id INTEGER,
 priority INTEGER NOT NULL DEFAULT 100,
 enabled INTEGER NOT NULL DEFAULT 1,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_fallback_chains (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 task TEXT NOT NULL DEFAULT 'general',
 model_id TEXT NOT NULL,
 position INTEGER NOT NULL DEFAULT 0,
 enabled INTEGER NOT NULL DEFAULT 1,
 UNIQUE(name,task,model_id)
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
    with _connect() as conn:
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
    """Promote the next eligible key instead of re-selecting the current key."""
    assert_mutation_allowed(f"llm-provider-key-rotate:{provider_id}")
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,key_name,active,priority FROM llm_provider_keys WHERE provider_id=? ORDER BY active DESC, priority, id",
            (int(provider_id),),
        ).fetchall()
        if not rows:
            raise ValueError("no provider keys configured")
        current = next((r for r in rows if bool(r["active"])), None)
        candidates = [r for r in rows if not bool(r["active"])]
        if not current:
            chosen = rows[0]
        elif not candidates:
            raise ValueError("no inactive provider key available for rotation")
        else:
            chosen = candidates[0]
        conn.execute("UPDATE llm_provider_keys SET active=0 WHERE provider_id=?", (int(provider_id),))
        conn.execute("UPDATE llm_provider_keys SET active=1,last_used_at=? WHERE id=?", (time.time(), int(chosen["id"])))
        conn.commit()
    return {"provider_id": provider_id, "active_key": str(chosen["key_name"]), "previous_key": str(current["key_name"]) if current else None}


def activate_provider_key(provider_id: int, key_name: str) -> dict[str, Any]:
    assert_mutation_allowed(f"llm-provider-key-activate:{provider_id}:{key_name}")
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT id,key_name FROM llm_provider_keys WHERE provider_id=? AND key_name=?", (int(provider_id), str(key_name).strip())).fetchone()
        if not row:
            raise ValueError("provider key not found")
        conn.execute("UPDATE llm_provider_keys SET active=0 WHERE provider_id=?", (int(provider_id),))
        conn.execute("UPDATE llm_provider_keys SET active=1,last_used_at=? WHERE id=?", (time.time(), int(row["id"])))
        conn.commit()
    return {"provider_id": provider_id, "active_key": str(row["key_name"])}


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
    provider_id: int | None = None,
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
    assert_mutation_allowed(f"llm-provider:{provider_id or name}")
    name, protocol, endpoint = name.strip(), protocol.strip(), endpoint.strip()
    if not name or not protocol or not endpoint:
        raise ValueError("provider name, protocol and endpoint are required")
    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        raise ValueError("provider endpoint must use http:// or https://")
    if timeout_seconds <= 0:
        raise ValueError("provider timeout must be positive")
    if provider_id is not None and int(provider_id) <= 0:
        raise ValueError("provider_id must be positive")
    ensure_schema()
    now = time.time()
    encrypted = _encrypt(secret) if secret else ""
    with connect() as conn:
        if provider_id is not None:
            existing = conn.execute("SELECT id,auth_secret FROM llm_providers WHERE id=?", (int(provider_id),)).fetchone()
            if not existing:
                raise KeyError(f"Unknown provider id: {provider_id}")
            conn.execute(
                """UPDATE llm_providers
                   SET name=?,protocol=?,endpoint=?,auth_type=?,
                       auth_secret=CASE WHEN ?='' THEN auth_secret ELSE ? END,
                       capabilities_json=?,version=?,enabled=?,timeout_seconds=?,updated_at=?
                   WHERE id=?""",
                (name, protocol, endpoint, auth_type, encrypted, encrypted,
                 json.dumps(capabilities or {}, ensure_ascii=False), version, int(enabled), timeout_seconds, now, int(provider_id)),
            )
            row = conn.execute("SELECT * FROM llm_providers WHERE id=?", (int(provider_id),)).fetchone()
        else:
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
        "auth_header": "Authorization", "auth_scheme": "Bearer",
        "api_key": secret, "key_name": key_name,
        "capabilities": json.loads(provider["capabilities_json"] or "{}"),
        "version": str(provider["version"] or ""), "timeout_seconds": float(provider["timeout_seconds"] or 30),
        "enabled": bool(provider["enabled"]),
    }

def set_routing_rule(task: str, model_id: str, *, provider_id: int | None = None, priority: int = 100, enabled: bool = True) -> dict[str, Any]:
    assert_mutation_allowed(f"llm-routing:{task}")
    task, model_id = str(task).strip().lower(), str(model_id).strip()
    if not task or not model_id or priority < 0:
        raise ValueError("task, model_id and non-negative priority are required")
    ensure_schema()
    now = time.time()
    with connect() as conn:
        conn.execute("""INSERT INTO llm_routing_rules(task,model_id,provider_id,priority,enabled,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(task) DO UPDATE SET model_id=excluded.model_id,
            provider_id=excluded.provider_id,priority=excluded.priority,enabled=excluded.enabled,updated_at=excluded.updated_at""",
            (task, model_id, provider_id, priority, int(enabled), now, now))
        row = conn.execute("SELECT * FROM llm_routing_rules WHERE task=?", (task,)).fetchone()
        conn.commit()
    return dict(row) | {"enabled": bool(row["enabled"])}

def list_routing_rules(*, task: str | None = None, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_schema()
    clauses, params = [], []
    if task: clauses.append("task=?"); params.append(str(task).strip().lower())
    if not include_disabled: clauses.append("enabled=1")
    q = "SELECT * FROM llm_routing_rules" + ((" WHERE " + " AND ".join(clauses)) if clauses else "") + " ORDER BY priority,task"
    with connect() as conn:
        return [dict(r) | {"enabled": bool(r["enabled"])} for r in conn.execute(q, params).fetchall()]

def delete_routing_rule(task: str) -> bool:
    assert_mutation_allowed(f"llm-routing-delete:{task}")
    ensure_schema()
    with connect() as conn:
        cur = conn.execute("DELETE FROM llm_routing_rules WHERE task=?", (str(task).strip().lower(),))
        conn.commit()
    return cur.rowcount > 0

def set_fallback_chain(name: str, task: str, model_ids: list[str], *, enabled: bool = True) -> list[dict[str, Any]]:
    assert_mutation_allowed(f"llm-fallback:{name}:{task}")
    name, task = str(name).strip(), str(task).strip().lower()
    model_ids = list(dict.fromkeys(str(x).strip() for x in model_ids if str(x).strip()))
    if not name or not task or not model_ids:
        raise ValueError("fallback name, task and at least one model are required")
    ensure_schema()
    with connect() as conn:
        conn.execute("DELETE FROM llm_fallback_chains WHERE name=? AND task=?", (name, task))
        for position, model_id in enumerate(model_ids):
            conn.execute("INSERT INTO llm_fallback_chains(name,task,model_id,position,enabled) VALUES(?,?,?,?,?)",
                         (name, task, model_id, position, int(enabled)))
        conn.commit()
    return list_fallback_chain(name, task)

def list_fallback_chain(name: str, task: str = "general") -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM llm_fallback_chains WHERE name=? AND task=? AND enabled=1 ORDER BY position,id",
                            (str(name).strip(), str(task).strip().lower())).fetchall()
    return [dict(r) | {"enabled": bool(r["enabled"])} for r in rows]

def delete_fallback_chain(name: str, task: str = "general") -> bool:
    assert_mutation_allowed(f"llm-fallback-delete:{name}:{task}")
    ensure_schema()
    with connect() as conn:
        cur = conn.execute("DELETE FROM llm_fallback_chains WHERE name=? AND task=?", (str(name).strip(), str(task).strip().lower()))
        conn.commit()
    return cur.rowcount > 0


def import_catalog(payload: dict[str, Any]) -> dict[str, int]:
    """Import provider/model metadata while preserving existing secrets."""
    if not isinstance(payload, dict) or int(payload.get("version", 0)) not in {1, 2}: raise ValueError("Unsupported catalog version.")
    imported = {"providers": 0, "models": 0}; provider_ids: dict[str, int] = {}
    for item in payload.get('providers', []):
        current = upsert_provider(name=str(item['name']), protocol=str(item['protocol']), endpoint=str(item['endpoint']), auth_type=str(item.get('auth_type','none')), capabilities=dict(item.get('capabilities') or {}), version=str(item.get('version','')), timeout_seconds=float(item.get('timeout_seconds',30)), enabled=bool(item.get('enabled',True)))
        provider_ids[str(item['name'])] = int(current['id']); imported['providers'] += 1
    for item in payload.get('models', []):
        pid = provider_ids.get(str(item.get('provider_name','')), int(item.get('provider_id',0)))
        if pid <= 0: raise ValueError("Model record references an unknown provider.")
        upsert_model(provider_id=pid, model_id=str(item['model_id']), tasks=list(item.get('tasks') or []), context_length=item.get('context_length'), limits=dict(item.get('limits') or {}), priority=int(item.get('priority',100)), version=str(item.get('version','')), enabled=bool(item.get('enabled',True)))
        imported['models'] += 1
    for rule in payload.get('routing_rules', []):
        set_routing_rule(str(rule['task']), str(rule['model_id']), provider_id=rule.get('provider_id'), priority=int(rule.get('priority',100)), enabled=bool(rule.get('enabled',True)))
    grouped = {}
    for row in payload.get('fallback_chains', []):
        grouped.setdefault((str(row['name']), str(row.get('task','general'))), []).append(row)
    for (name, task), rows in grouped.items():
        set_fallback_chain(name, task, [x['model_id'] for x in sorted(rows, key=lambda z:int(z.get('position',0)))], enabled=all(bool(x.get('enabled',True)) for x in rows))
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
    with connect() as conn:
        rules = [dict(r) for r in conn.execute("SELECT * FROM llm_routing_rules ORDER BY priority,task").fetchall()]
        chains = [dict(r) for r in conn.execute("SELECT * FROM llm_fallback_chains ORDER BY name,task,position").fetchall()]
    for row in rules + chains:
        row.pop("created_at", None); row.pop("updated_at", None)
    return {"version": 2, "providers": providers, "models": models, "routing_rules": rules, "fallback_chains": chains}
