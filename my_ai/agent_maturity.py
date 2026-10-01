from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from .db import execute, fetch_all
from .project_workspace import PROJECTS_ROOT, project_slug

STATES = frozenset({
    "received", "understood", "planned", "authorized", "running",
    "validating", "repairing", "completed", "failed", "blocked", "rolled_back",
})
_ALLOWED_TRANSITIONS = {
    "received": {"understood", "blocked", "failed"},
    "understood": {"planned", "blocked", "failed"},
    "planned": {"authorized", "blocked", "failed"},
    "authorized": {"running", "blocked", "failed"},
    "running": {"validating", "failed", "rolled_back"},
    "validating": {"completed", "repairing", "failed", "rolled_back"},
    "repairing": {"validating", "failed", "rolled_back"},
    "completed": set(),
    "failed": set(),
    "blocked": set(),
    "rolled_back": set(),
}


def ensure_maturity_schema() -> None:
    execute("""CREATE TABLE IF NOT EXISTS agent_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, task_key TEXT NOT NULL UNIQUE,
        goal TEXT NOT NULL, state TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    execute("""CREATE TABLE IF NOT EXISTS task_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL, state TEXT NOT NULL,
        event TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    execute("""CREATE TABLE IF NOT EXISTS repair_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL, iteration INTEGER NOT NULL,
        defect TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '[]', proposal TEXT NOT NULL,
        validation TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    execute("""CREATE TABLE IF NOT EXISTS tool_manifests (
        name TEXT NOT NULL, version TEXT NOT NULL, manifest TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(name, version)
    )""")
    execute("""CREATE TABLE IF NOT EXISTS agent_config_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT NOT NULL UNIQUE,
        config TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    execute("""CREATE TABLE IF NOT EXISTS task_workspaces (
        task_id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, cleaned_at TEXT
    )""")


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True, default=str)


def create_task(goal: str, session_id: int | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_maturity_schema()
    clean = " ".join(str(goal or "").split()).strip()
    if not clean:
        raise ValueError("task goal must not be empty")
    task_key = "task:" + hashlib.sha256((clean + ":" + uuid.uuid4().hex).encode()).hexdigest()[:24]
    task_id = execute(
        "INSERT INTO agent_tasks(session_id,task_key,goal,state,metadata) VALUES(?,?,?,?,?)",
        (session_id, task_key, clean, "received", _json(metadata)),
    )
    execute("INSERT INTO task_events(task_id,state,event,payload) VALUES(?,?,?,?)", (task_id, "received", "created", _json(metadata)))
    return get_task(task_id)


def get_task(task_id: int) -> dict[str, Any]:
    ensure_maturity_schema()
    rows = fetch_all("SELECT * FROM agent_tasks WHERE id=?", (int(task_id),))
    if not rows:
        raise KeyError(f"task {task_id} not found")
    row = dict(rows[0])
    try:
        row["metadata"] = json.loads(row.get("metadata") or "{}")
    except (TypeError, ValueError):
        row["metadata"] = {}
    return row


def transition_task(task_id: int, state: str, event: str = "transition", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_maturity_schema()
    target = str(state).strip()
    if target not in STATES:
        raise ValueError("invalid task state")
    task = get_task(task_id)
    current = str(task["state"])
    if target != current and target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid task transition: {current} -> {target}")
    execute("UPDATE agent_tasks SET state=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (target, int(task_id)))
    execute("INSERT INTO task_events(task_id,state,event,payload) VALUES(?,?,?,?)", (task_id, target, str(event), _json(payload)))
    return get_task(task_id)


def task_trace(task_id: int, limit: int = 200) -> list[dict[str, Any]]:
    ensure_maturity_schema()
    rows = fetch_all(
        "SELECT id,state,event,payload,created_at FROM task_events WHERE task_id=? ORDER BY id DESC LIMIT ?",
        (int(task_id), max(1, min(int(limit), 1000))),
    )
    for row in rows:
        try:
            row["payload"] = json.loads(row.get("payload") or "{}")
        except (TypeError, ValueError):
            row["payload"] = {}
    return list(reversed(rows))


@dataclass(frozen=True)
class RepairResult:
    status: str
    iterations: int
    validation: Any
    attempts: tuple[dict[str, Any], ...]


def verify_critique_repair_verify(
    validate: Callable[[], Any],
    critique: Callable[[Any], Any],
    repair: Callable[[Any, Any], Any],
    *,
    max_iterations: int = 3,
    record: Callable[[int, str, Any, Any, Any, str], None] | None = None,
) -> RepairResult:
    max_iterations = max(0, min(int(max_iterations), 10))
    attempts: list[dict[str, Any]] = []
    validation = validate()
    for iteration in range(max_iterations + 1):
        if bool(validation):
            return RepairResult("passed", iteration, validation, tuple(attempts))
        if iteration == max_iterations:
            return RepairResult("failed", iteration, validation, tuple(attempts))
        defect = critique(validation)
        proposal = repair(defect, validation)
        outcome = validate()
        status = "passed" if bool(outcome) else "failed"
        item = {
            "iteration": iteration + 1,
            "defect": defect,
            "proposal": proposal,
            "validation": outcome,
            "status": status,
        }
        attempts.append(item)
        if record is not None:
            record(iteration + 1, str(defect), [], proposal, outcome, status)
        validation = outcome
    return RepairResult("failed", max_iterations, validation, tuple(attempts))


def record_repair(task_id: int, iteration: int, defect: str, evidence: list[Any], proposal: Any, validation: Any, status: str) -> int:
    ensure_maturity_schema()
    return execute(
        "INSERT INTO repair_attempts(task_id,iteration,defect,evidence,proposal,validation,status) VALUES(?,?,?,?,?,?,?)",
        (task_id, int(iteration), defect, _json(evidence), _json(proposal), _json(validation), status),
    )


def _safe_relative(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root = root.resolve()
    resolved.relative_to(root)
    return resolved


def create_task_workspace(task_id: int, project_name: str = "task") -> Path:
    ensure_maturity_schema()
    base = (PROJECTS_ROOT / ".tasks").resolve()
    base.mkdir(parents=True, exist_ok=True)
    root = (base / project_slug(project_name) / str(int(task_id))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _safe_relative(root, base)
    execute("INSERT OR REPLACE INTO task_workspaces(task_id,path,cleaned_at) VALUES(?,?,NULL)", (int(task_id), str(root)))
    return root


def task_workspace(task_id: int) -> Path:
    rows = fetch_all("SELECT path FROM task_workspaces WHERE task_id=?", (int(task_id),))
    if not rows:
        raise KeyError(f"workspace for task {task_id} not found")
    return _safe_relative(Path(str(rows[0]["path"])), (PROJECTS_ROOT / ".tasks"))


def cleanup_task_workspace(task_id: int) -> None:
    path = task_workspace(task_id)
    if path.exists():
        shutil.rmtree(path)
    execute("UPDATE task_workspaces SET cleaned_at=CURRENT_TIMESTAMP WHERE task_id=?", (int(task_id),))


@dataclass
class TaskTransaction:
    task_id: int
    root: Path
    _files: dict[Path, bytes | None] = field(default_factory=dict)
    _committed: bool = False

    def stage_write(self, relative: str, content: str | bytes) -> Path:
        target = _safe_relative(self.root / relative, self.root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target not in self._files:
            self._files[target] = target.read_bytes()
        elif target not in self._files:
            self._files[target] = None
        data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        target.write_bytes(data)
        return target

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        for path, original in self._files.items():
            if original is not None:
                path.write_bytes(original)
            elif path.exists():
                path.unlink()
        self._committed = False


@contextlib.contextmanager
def task_transaction(task_id: int, root: Path | None = None) -> Iterator[TaskTransaction]:
    workspace = root or task_workspace(task_id)
    transaction = TaskTransaction(int(task_id), _safe_relative(workspace, (PROJECTS_ROOT / ".tasks")))
    try:
        yield transaction
    except Exception:
        transaction.rollback()
        raise
    if not transaction._committed:
        transaction.rollback()


def memory_lifecycle(knowledge_id: int, status: str) -> dict[str, Any]:
    allowed = {"temporary", "candidate", "validated", "trusted", "stale", "archived"}
    value = str(status).strip().lower()
    if value not in allowed:
        raise ValueError("invalid memory lifecycle")
    rows = fetch_all("SELECT id,verification_status FROM knowledge WHERE id=?", (int(knowledge_id),))
    if not rows:
        raise KeyError(f"knowledge {knowledge_id} not found")
    execute("UPDATE knowledge SET verification_status=? WHERE id=?", (value, int(knowledge_id)))
    return {"id": int(knowledge_id), "status": value, "previous": rows[0]["verification_status"]}


def memory_lifecycle_rows(limit: int = 100) -> list[dict[str, Any]]:
    return fetch_all(
        "SELECT id,title,topic,category,verification_status,source_url,confidence,verified_at,created_at FROM knowledge ORDER BY id DESC LIMIT ?",
        (max(1, min(int(limit), 500)),),
    )


def register_tool_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = ("name", "version", "input_schema", "output_schema", "risk", "offline")
    if any(not str(manifest.get(key) or "").strip() and key not in {"offline"} for key in required):
        raise ValueError("tool manifest is missing required fields")
    normalized = dict(manifest)
    normalized["name"] = str(normalized["name"]).strip()
    normalized["version"] = str(normalized["version"]).strip()
    normalized["offline"] = bool(normalized.get("offline", True))
    normalized["enabled"] = bool(normalized.get("enabled", True))
    ensure_maturity_schema()
    execute(
        "INSERT OR REPLACE INTO tool_manifests(name,version,manifest,enabled) VALUES(?,?,?,?)",
        (normalized["name"], normalized["version"], _json(normalized), int(normalized["enabled"])),
    )
    return normalized


def tool_manifests() -> list[dict[str, Any]]:
    ensure_maturity_schema()
    rows = fetch_all("SELECT name,version,manifest,enabled,created_at FROM tool_manifests ORDER BY name,version")
    result = []
    for row in rows:
        try:
            item = json.loads(row["manifest"])
        except (TypeError, ValueError):
            item = {}
        item["enabled"] = bool(row["enabled"])
        item["created_at"] = row["created_at"]
        result.append(item)
    return result


def save_config_version(version: str, config: dict[str, Any], activate: bool = False) -> dict[str, Any]:
    ensure_maturity_schema()
    version = str(version).strip()
    if not version:
        raise ValueError("config version is required")
    if activate:
        execute("UPDATE agent_config_versions SET active=0")
    execute(
        "INSERT OR REPLACE INTO agent_config_versions(version,config,active) VALUES(?,?,?)",
        (version, _json(config), int(activate)),
    )
    return config_version(version)


def config_version(version: str) -> dict[str, Any]:
    rows = fetch_all("SELECT id,version,config,active,created_at FROM agent_config_versions WHERE version=?", (str(version),))
    if not rows:
        raise KeyError(f"config version {version} not found")
    row = dict(rows[0])
    try:
        row["config"] = json.loads(row["config"])
    except (TypeError, ValueError):
        row["config"] = {}
    row["active"] = bool(row["active"])
    return row


def config_versions() -> list[dict[str, Any]]:
    ensure_maturity_schema()
    rows = fetch_all("SELECT id,version,config,active,created_at FROM agent_config_versions ORDER BY id DESC")
    result = []
    for row in rows:
        try:
            row["config"] = json.loads(row["config"])
        except (TypeError, ValueError):
            row["config"] = {}
        row["active"] = bool(row["active"])
        result.append(row)
    return result


class CircuitBreaker:
    def __init__(self, threshold: int = 3, reset_seconds: float = 30.0):
        self.threshold = max(1, int(threshold))
        self.reset_seconds = max(1.0, float(reset_seconds))
        self._failures = 0
        self._opened_at = 0.0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if not self._opened_at:
                return True
            if time.monotonic() - self._opened_at >= self.reset_seconds:
                self._opened_at = 0.0
                self._failures = 0
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = 0.0

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold:
                self._opened_at = time.monotonic()

    def status(self) -> dict[str, Any]:
        with self._lock:
            opened = bool(self._opened_at)
            if opened and time.monotonic() - self._opened_at >= self.reset_seconds:
                opened = False
            return {"failures": self._failures, "open": opened}

_CIRCUITS: dict[str, CircuitBreaker] = {}
_CIRCUITS_LOCK = threading.Lock()


def circuit(name: str) -> CircuitBreaker:
    key = str(name).strip()
    with _CIRCUITS_LOCK:
        if key not in _CIRCUITS:
            _CIRCUITS[key] = CircuitBreaker()
        return _CIRCUITS[key]


def maturity_summary() -> dict[str, Any]:
    ensure_maturity_schema()
    tasks = fetch_all("SELECT state,COUNT(*) AS count FROM agent_tasks GROUP BY state")
    return {
        "task_states": {str(row["state"]): int(row["count"]) for row in tasks},
        "tools": len(tool_manifests()),
        "config_versions": len(config_versions()),
        "workspaces": len(fetch_all("SELECT task_id FROM task_workspaces WHERE cleaned_at IS NULL")),
    }


__all__ = [
    "STATES", "create_task", "get_task", "transition_task", "task_trace",
    "verify_critique_repair_verify", "record_repair", "create_task_workspace",
    "task_workspace", "cleanup_task_workspace", "task_transaction",
    "memory_lifecycle", "memory_lifecycle_rows", "register_tool_manifest",
    "tool_manifests", "save_config_version", "config_version", "config_versions",
    "CircuitBreaker", "circuit", "maturity_summary", "ensure_maturity_schema",
]
