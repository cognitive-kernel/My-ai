"""Versioned learning source catalog with approval, provenance and ranking."""
from __future__ import annotations
import hashlib, time
from typing import Any
from .db import connect


SCHEMA="""CREATE TABLE IF NOT EXISTS learning_source_catalog(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER,
 topic_id INTEGER,
 url TEXT NOT NULL,
 source_type TEXT NOT NULL DEFAULT 'custom',
 title TEXT NOT NULL DEFAULT '',
 priority INTEGER NOT NULL DEFAULT 100,
 weight REAL NOT NULL DEFAULT 1,
 status TEXT NOT NULL DEFAULT 'pending',
 content_hash TEXT NOT NULL DEFAULT '',
 content_version INTEGER NOT NULL DEFAULT 1,
 product TEXT NOT NULL DEFAULT '',
 version TEXT NOT NULL DEFAULT '',
 compatibility TEXT NOT NULL DEFAULT '',
 provenance_json TEXT NOT NULL DEFAULT '{}',
 discovered_at REAL NOT NULL,
 reviewed_at REAL
);"""


def ensure_schema():
    with connect() as c:
        c.executescript(SCHEMA)
        columns={str(r["name"]) for r in c.execute("PRAGMA table_info(learning_source_catalog)").fetchall()}
        if "content_version" not in columns:
            c.execute("ALTER TABLE learning_source_catalog ADD COLUMN content_version INTEGER NOT NULL DEFAULT 1")
        c.commit()


def add_source(url, *, course_id=None, topic_id=None, source_type="custom", title="", priority=100, weight=1,
               product="", version="", compatibility="", provenance=None):
    ensure_schema()
    if not str(url).startswith(("http://","https://","file://")): raise ValueError("unsupported source URL")
    with connect() as c:
        cur=c.execute("""INSERT INTO learning_source_catalog
        (course_id,topic_id,url,source_type,title,priority,weight,product,version,compatibility,provenance_json,discovered_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(course_id,topic_id,url,source_type,title,priority,weight,product,version,compatibility,
        __import__("json").dumps(provenance or {},ensure_ascii=False),time.time()))
        c.commit()
        return get_source(cur.lastrowid)


def get_source(source_id):
    ensure_schema()
    with connect() as c:
        r=c.execute("SELECT * FROM learning_source_catalog WHERE id=?",(source_id,)).fetchone()
    if not r:return None
    x=dict(r); x["provenance"]=__import__("json").loads(x.pop("provenance_json") or "{}"); return x


def list_sources(course_id=None, topic_id=None, status=None):
    ensure_schema()
    clauses=[]; params=[]
    if course_id is not None: clauses.append("course_id=?"); params.append(course_id)
    if topic_id is not None: clauses.append("topic_id=?"); params.append(topic_id)
    if status: clauses.append("status=?"); params.append(status)
    q="SELECT * FROM learning_source_catalog"+((" WHERE "+" AND ".join(clauses)) if clauses else "")+" ORDER BY priority,weight DESC,id"
    with connect() as c: rows=c.execute(q,params).fetchall()
    out=[]
    for r in rows:
        x=dict(r); x["provenance"]=__import__("json").loads(x.pop("provenance_json") or "{}"); out.append(x)
    return out


def update_source(source_id: int, **changes) -> dict[str, Any] | None:
    ensure_schema()
    allowed = {'url','source_type','title','priority','weight','product','version','compatibility','course_id','topic_id'}
    changes = {k:v for k,v in changes.items() if k in allowed}
    if 'url' in changes and not str(changes['url']).startswith(('http://','https://','file://')): raise ValueError('unsupported source URL')
    if not changes: return get_source(source_id)
    with connect() as c:
        if not c.execute('SELECT id FROM learning_source_catalog WHERE id=?',(int(source_id),)).fetchone(): return None
        sets=', '.join(f'{k}=?' for k in changes)
        c.execute(f'UPDATE learning_source_catalog SET {sets} WHERE id=?', tuple(changes.values())+(int(source_id),)); c.commit()
    return get_source(source_id)

def delete_source(source_id: int) -> bool:
    ensure_schema()
    with connect() as c:
        cur=c.execute('DELETE FROM learning_source_catalog WHERE id=?',(int(source_id),)); c.commit()
    return cur.rowcount > 0

def review_source(source_id,status):
    if status not in {"approved","rejected","pending","recheck","deprecated"}: raise ValueError("invalid source status")
    ensure_schema()
    with connect() as c:
        c.execute("UPDATE learning_source_catalog SET status=?,reviewed_at=? WHERE id=?",(status,time.time(),source_id)); c.commit()
    return get_source(source_id)


def update_content_hash(source_id,content):
    digest=hashlib.sha256(str(content).encode("utf-8")).hexdigest()
    ensure_schema()
    with connect() as c:
        old=c.execute("SELECT content_hash,content_version FROM learning_source_catalog WHERE id=?",(source_id,)).fetchone()
        changed=bool(old and old["content_hash"] and old["content_hash"]!=digest)
        version=int(old["content_version"] or 1) + (1 if changed else 0) if old else 1
        c.execute("UPDATE learning_source_catalog SET content_hash=?,content_version=?,status=? WHERE id=?",
                  (digest,version,"recheck" if changed else "pending",source_id))
        if changed:
            c.execute("""INSERT INTO learning_relearning_queue(source_id,reason,old_hash,new_hash,created_at)
                         VALUES(?,?,?,?,?)""",(source_id,"source-content-changed",str(old["content_hash"]),digest,time.time()))
        c.commit()
    return {"source_id":source_id,"hash":digest,"changed":changed,"content_version":version,"relearning_queued":changed}

def list_relearning_queue(*, source_id: int | None = None, status: str = "pending", limit: int = 100) -> list[dict[str, Any]]:
    ensure_schema()
    clauses, params = [], []
    if source_id is not None: clauses.append("source_id=?"); params.append(int(source_id))
    if status: clauses.append("status=?"); params.append(str(status))
    params.append(max(1,min(500,int(limit))))
    q="SELECT * FROM learning_relearning_queue"+((" WHERE "+" AND ".join(clauses)) if clauses else "")+" ORDER BY created_at,id LIMIT ?"
    with connect() as c: return [dict(r) for r in c.execute(q,params).fetchall()]

def claim_relearning_job(job_id: int) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as c:
        c.execute("UPDATE learning_relearning_queue SET status='processing' WHERE id=? AND status='pending'",(int(job_id),))
        row=c.execute("SELECT * FROM learning_relearning_queue WHERE id=?",(int(job_id),)).fetchone(); c.commit()
    return dict(row) if row else None

def complete_relearning_job(job_id: int, *, success: bool = True) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as c:
        status="completed" if success else "failed"
        c.execute("UPDATE learning_relearning_queue SET status=?,processed_at=? WHERE id=? AND status='processing'",(status,time.time(),int(job_id)))
        row=c.execute("SELECT * FROM learning_relearning_queue WHERE id=?",(int(job_id),)).fetchone(); c.commit()
    return dict(row) if row else None
