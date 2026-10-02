"""Persistent evaluation and regression registry for no-code agent improvement workflows."""
from __future__ import annotations
import json, time, uuid
from typing import Any, Callable
from .db import connect
from .access_policy import assert_mutation_allowed

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluation_suites(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 tasks_json TEXT NOT NULL,
 version TEXT NOT NULL DEFAULT '1',
 enabled INTEGER NOT NULL DEFAULT 1,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_baselines(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 suite_id INTEGER NOT NULL,
 label TEXT NOT NULL,
 metrics_json TEXT NOT NULL,
 created_at REAL NOT NULL,
 UNIQUE(suite_id,label),
 FOREIGN KEY(suite_id) REFERENCES evaluation_suites(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evaluation_runs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 suite_id INTEGER NOT NULL,
 candidate TEXT NOT NULL DEFAULT '',
 metrics_json TEXT NOT NULL,
 results_json TEXT NOT NULL,
 baseline_id INTEGER,
 status TEXT NOT NULL DEFAULT 'completed',
 created_at REAL NOT NULL,
 FOREIGN KEY(suite_id) REFERENCES evaluation_suites(id) ON DELETE CASCADE,
 FOREIGN KEY(baseline_id) REFERENCES evaluation_baselines(id)
);
CREATE TABLE IF NOT EXISTS evaluation_candidates(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 candidate_id TEXT NOT NULL UNIQUE,
 name TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 baseline_run_id INTEGER,
 verification_json TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL DEFAULT 'candidate',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL
);
"""

def ensure_schema():
    with connect() as c:
        c.executescript(SCHEMA)
        c.commit()

def upsert_suite(name:str,tasks:list[dict[str,Any]],version:str="1",enabled:bool=True)->dict[str,Any]:
    assert_mutation_allowed(f"evaluation-suite:{name}")
    if not name.strip() or not tasks: raise ValueError("suite name and tasks are required")
    ensure_schema(); now=time.time()
    with connect() as c:
        c.execute("""INSERT INTO evaluation_suites(name,tasks_json,version,enabled,created_at,updated_at)
                     VALUES(?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET tasks_json=excluded.tasks_json,
                     version=excluded.version,enabled=excluded.enabled,updated_at=excluded.updated_at""",
                  (name.strip(),json.dumps(tasks,ensure_ascii=False),version,int(enabled),now,now))
        row=c.execute("SELECT * FROM evaluation_suites WHERE name=?",(name.strip(),)).fetchone(); c.commit()
    return _suite(row)

def _suite(row):
    if not row:return None
    x=dict(row); x["tasks"]=json.loads(x.pop("tasks_json") or "[]"); x["enabled"]=bool(x["enabled"]); return x

def list_suites()->list[dict[str,Any]]:
    ensure_schema()
    with connect() as c: rows=c.execute("SELECT * FROM evaluation_suites ORDER BY name").fetchall()
    return [_suite(r) for r in rows]

def record_run(suite_id:int,candidate:str,metrics:dict[str,Any],results:list[dict[str,Any]],baseline_id:int|None=None,status:str="completed")->dict[str,Any]:
    ensure_schema()
    with connect() as c:
        cur=c.execute("""INSERT INTO evaluation_runs(suite_id,candidate,metrics_json,results_json,baseline_id,status,created_at)
                         VALUES(?,?,?,?,?,?,?)""",(suite_id,candidate,json.dumps(metrics,ensure_ascii=False),json.dumps(results,ensure_ascii=False),baseline_id,status,time.time()))
        row=c.execute("SELECT * FROM evaluation_runs WHERE id=?",(cur.lastrowid,)).fetchone(); c.commit()
    return _run(row)

def _run(row):
    x=dict(row); x["metrics"]=json.loads(x.pop("metrics_json") or "{}"); x["results"]=json.loads(x.pop("results_json") or "[]"); return x

def create_baseline(suite_id:int,label:str,metrics:dict[str,Any])->dict[str,Any]:
    assert_mutation_allowed(f"evaluation-baseline:{suite_id}:{label}")
    ensure_schema()
    with connect() as c:
        c.execute("INSERT INTO evaluation_baselines(suite_id,label,metrics_json,created_at) VALUES(?,?,?,?) ON CONFLICT(suite_id,label) DO UPDATE SET metrics_json=excluded.metrics_json,created_at=excluded.created_at",
                  (suite_id,label,json.dumps(metrics,ensure_ascii=False),time.time()))
        row=c.execute("SELECT * FROM evaluation_baselines WHERE suite_id=? AND label=?",(suite_id,label)).fetchone(); c.commit()
    x=dict(row); x["metrics"]=json.loads(x.pop("metrics_json") or "{}"); return x

def propose_candidate(name:str,payload:dict[str,Any],baseline_run_id:int|None=None)->dict[str,Any]:
    assert_mutation_allowed(f"evaluation-candidate:{name}")
    ensure_schema(); cid=str(uuid.uuid4()); now=time.time()
    with connect() as c:
        c.execute("INSERT INTO evaluation_candidates(candidate_id,name,payload_json,baseline_run_id,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                  (cid,name,json.dumps(payload,ensure_ascii=False),baseline_run_id,now,now))
        c.commit()
    return get_candidate(cid)

def get_candidate(candidate_id:str)->dict[str,Any]|None:
    ensure_schema()
    with connect() as c: row=c.execute("SELECT * FROM evaluation_candidates WHERE candidate_id=?",(candidate_id,)).fetchone()
    if not row:return None
    x=dict(row); x["payload"]=json.loads(x.pop("payload_json") or "{}"); x["verification"]=json.loads(x.pop("verification_json") or "{}"); return x

def verify_candidate(candidate_id:str,verification:dict[str,Any],approved:bool=False)->dict[str,Any]:
    assert_mutation_allowed(f"evaluation-candidate-verify:{candidate_id}")
    ensure_schema(); status="approved" if approved and bool(verification.get("passed")) else ("verified" if bool(verification.get("passed")) else "rejected")
    with connect() as c:
        c.execute("UPDATE evaluation_candidates SET verification_json=?,status=?,updated_at=? WHERE candidate_id=?",
                  (json.dumps(verification,ensure_ascii=False),status,time.time(),candidate_id))
        c.commit()
    return get_candidate(candidate_id)

def list_candidates()->list[dict[str,Any]]:
    ensure_schema()
    with connect() as c: rows=c.execute("SELECT candidate_id FROM evaluation_candidates ORDER BY id DESC").fetchall()
    return [get_candidate(str(r["candidate_id"])) for r in rows]

def compare_metrics(candidate:dict[str,Any],baseline:dict[str,Any])->dict[str,Any]:
    keys=sorted(set(candidate)|set(baseline))
    return {k:{"candidate":candidate.get(k),"baseline":baseline.get(k),
               "delta":(float(candidate[k])-float(baseline[k])) if k in candidate and k in baseline and isinstance(candidate[k],(int,float)) and isinstance(baseline[k],(int,float)) else None}
            for k in keys}
