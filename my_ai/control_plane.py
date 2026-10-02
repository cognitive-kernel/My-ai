"""Unified configuration/control-plane persistence for no-code management.

This module intentionally keeps the control plane independent from business logic.
Runtime modules consume these records through small adapters instead of embedding
mutable policy in source code.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .db import connect


SCHEMA = """
CREATE TABLE IF NOT EXISTS control_plane_records (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(namespace, name)
);
CREATE TABLE IF NOT EXISTS control_plane_history (id INTEGER PRIMARY KEY AUTOINCREMENT,namespace TEXT NOT NULL,name TEXT NOT NULL,version INTEGER NOT NULL,payload_json TEXT NOT NULL,enabled INTEGER NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS control_plane_audit (id INTEGER PRIMARY KEY AUTOINCREMENT,namespace TEXT NOT NULL,name TEXT NOT NULL,action TEXT NOT NULL,version INTEGER NOT NULL,details TEXT NOT NULL DEFAULT '',created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS control_plane_actions (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    namespace TEXT NOT NULL,
    target_id TEXT,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


@dataclass(frozen=True)
class ControlRecord:
    id: str
    namespace: str
    name: str
    payload: dict[str, Any]
    version: int
    enabled: bool
    created_at: float
    updated_at: float


def ensure_schema() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _decode(row) -> ControlRecord:
    return ControlRecord(
        id=str(row["id"]),
        namespace=str(row["namespace"]),
        name=str(row["name"]),
        payload=json.loads(row["payload_json"] or "{}"),
        version=int(row["version"]),
        enabled=bool(row["enabled"]),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
    )


def list_records(namespace: str | None = None, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_schema()
    sql = "SELECT * FROM control_plane_records"
    clauses, params = [], []
    if namespace:
        clauses.append("namespace=?")
        params.append(namespace)
    if not include_disabled:
        clauses.append("enabled=1")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY namespace, name"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [r.__dict__ for r in map(_decode, rows)]


def get_record(namespace: str, name: str) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM control_plane_records WHERE namespace=? AND name=?",
            (namespace, name),
        ).fetchone()
    return _decode(row).__dict__ if row else None


def _validate_payload(namespace: str, name: str, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict): raise ValueError("payload must be an object")
    if not namespace.strip() or not name.strip(): raise ValueError("namespace and name are required")
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 512_000: raise ValueError("payload exceeds 512 KiB")
    if "version" in payload:
        try:
            if int(payload["version"]) < 1: raise ValueError("version must be positive")
        except (TypeError, ValueError) as exc: raise ValueError("version must be a positive integer") from exc


def put_record(
    namespace: str,
    name: str,
    payload: dict[str, Any] | None = None,
    *,
    enabled: bool = True,
    record_id: str | None = None,
) -> dict[str, Any]:
    ensure_schema()
    namespace, name = namespace.strip(), name.strip()
    _validate_payload(namespace, name, payload or {})
    now = time.time()
    with connect() as conn:
        existing = conn.execute(
            "SELECT id,version,created_at FROM control_plane_records WHERE namespace=? AND name=?",
            (namespace, name),
        ).fetchone()
        rid = str(existing["id"]) if existing else (record_id or str(uuid.uuid4()))
        version = int(existing["version"]) + 1 if existing else 1
        created = float(existing["created_at"]) if existing else now
        conn.execute(
            """INSERT INTO control_plane_records
               (id,namespace,name,payload_json,version,enabled,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(namespace,name) DO UPDATE SET
                 payload_json=excluded.payload_json,
                 version=excluded.version,
                 enabled=excluded.enabled,
                 updated_at=excluded.updated_at""",
            (rid, namespace, name, json.dumps(payload or {}, ensure_ascii=False),
             version, int(enabled), created, now),
        )
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        conn.execute("INSERT INTO control_plane_history(namespace,name,version,payload_json,enabled,created_at) VALUES(?,?,?,?,?,?)",
                     (namespace, name, version, payload_json, int(enabled), now))
        conn.execute("INSERT INTO control_plane_audit(namespace,name,action,version,details,created_at) VALUES(?,?,?,?,?,?)",
                     (namespace, name, "upsert", version, "control-plane mutation", now))
        conn.commit()
    return get_record(namespace, name) or {}


def set_enabled(namespace: str, name: str, enabled: bool) -> dict[str, Any]:
    current = get_record(namespace, name)
    if not current:
        raise KeyError(f"{namespace}/{name}")
    return put_record(namespace, name, current["payload"], enabled=enabled, record_id=current["id"])


def delete_record(namespace: str, name: str) -> bool:
    ensure_schema()
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM control_plane_records WHERE namespace=? AND name=?",
            (namespace, name),
        )
        conn.commit()
    return cur.rowcount > 0


def start_action(action: str, namespace: str, target_id: str | None = None) -> dict[str, Any]:
    ensure_schema()
    now = time.time()
    action_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            """INSERT INTO control_plane_actions
               (id,action,namespace,target_id,status,progress,result_json,error,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (action_id, action, namespace, target_id, "started", 0, "{}", "", now, now),
        )
        conn.commit()
    return get_action(action_id)


def update_action(action_id: str, *, status: str, progress: float = 0,
                  result: dict[str, Any] | None = None, error: str = "") -> dict[str, Any]:
    ensure_schema()
    with connect() as conn:
        conn.execute(
            """UPDATE control_plane_actions SET status=?,progress=?,result_json=?,error=?,updated_at=?
               WHERE id=?""",
            (status, max(0, min(100, float(progress))),
             json.dumps(result or {}, ensure_ascii=False), error, time.time(), action_id),
        )
        conn.commit()
    return get_action(action_id)


def get_action(action_id: str) -> dict[str, Any]:
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT * FROM control_plane_actions WHERE id=?", (action_id,)).fetchone()
    if not row:
        raise KeyError(action_id)
    item = dict(row)
    item["progress"] = float(item["progress"])
    item["result"] = json.loads(item.pop("result_json") or "{}")
    return item


def list_actions(limit: int = 100) -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM control_plane_actions ORDER BY updated_at DESC LIMIT ?",
            (max(1, min(1000, int(limit))),),
        ).fetchall()
    return [dict(r) | {"result": json.loads(r["result_json"] or "{}")} for r in rows]


DEFAULT_NAMESPACES = (
    "agent.behavior", "agent.workflow", "agent.planning", "agent.routing",
    "agent.session", "tools.catalog", "tools.http", "tools.webhook", "tools.command",
    "memory.short_term", "memory.long_term", "memory.experiential", "memory.policy",
    "research.providers", "research.sources", "research.policy",
    "security.roles", "security.capabilities", "security.network", "security.filesystem",
    "security.subprocess", "security.approvals", "security.self_modification",
    "self_update.policy", "self_repair.policy", "self_improvement.policy",
    "scheduler.jobs", "scheduler.resources", "scheduler.quotas",
    "multimodal.image", "multimodal.voice", "multimodal.routing",
    "execution.profiles", "execution.projects", "execution.environments",
    "integrations.catalog", "integrations.events", "integrations.webhooks",
    "server.policy", "server.notifications",
    "observability.logs", "observability.metrics", "observability.traces",
    "observability.telemetry", "observability.alerts", "observability.dashboard",
    "database.backup", "database.migration",
    "prompts.registry", "policies.registry", "config.profiles", "ui.actions",
    "plugins.registry", "skills.registry", "knowledge.registry",
    "evaluation.benchmarks", "evaluation.regression", "evaluation.ab",
    "experience.evolution", "experience.lessons", "agent.skills", "agent.knowledge_graph",
    "agent.retrieval", "agent.context", "agent.verification", "agent.confidence",
    "agent.cache", "agent.budget", "agent.events", "agent.meta", "agent.os",
    "research.agent", "execution.sandbox", "execution.snapshots",
)


def namespace_catalog() -> list[str]:
    return list(DEFAULT_NAMESPACES)


def list_history(namespace: str, name: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    ensure_schema()
    sql = "SELECT id,namespace,name,version,payload_json,enabled,created_at FROM control_plane_history WHERE namespace=?"
    params = [namespace]
    if name:
        sql += " AND name=?"
        params.append(name)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(1000, int(limit))))
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) | {"payload": json.loads(r["payload_json"] or "{}"), "enabled": bool(r["enabled"])} for r in rows]


def export_namespace(namespace: str) -> dict[str, Any]:
    return {"namespace": namespace, "version": 1, "records": list_records(namespace, include_disabled=True)}


def import_namespace(namespace: str, records: list[dict[str, Any]]) -> int:
    if not isinstance(records, list): raise ValueError("records must be a list")
    count = 0
    for record in records:
        if not isinstance(record, dict) or not str(record.get("name", "")).strip(): raise ValueError("each record requires a name")
        put_record(namespace, str(record["name"]), dict(record.get("payload") or {}), enabled=bool(record.get("enabled", True)))
        count += 1
    return count
