"""Persistent event -> action mappings with idempotency metadata."""
from __future__ import annotations
import hashlib, json, time
from .control_plane import put_record, get_record
from .db import connect

def _ensure_schema():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS integration_event_delivery(
            event_id TEXT PRIMARY KEY, event TEXT NOT NULL, payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
        conn.commit()

def register_event(event: str, action: dict, *, enabled=True, retry=3, dead_letter=True):
    return put_record("integrations.events",event,{"action":action,"retry":retry,"dead_letter":dead_letter},enabled=enabled)

def event_key(event: str, payload) -> str:
    return hashlib.sha256((event+"|"+json.dumps(payload,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()

def dispatch(event: str, payload, executor, *, event_id=None):
    _ensure_schema()
    cfg=get_record("integrations.events",event)
    if not cfg or not cfg.get("enabled"): return {"status":"ignored","reason":"event-disabled"}
    action=cfg["payload"].get("action",{})
    delivery_id=str(event_id or event_key(event,payload))
    import json
    with connect() as conn:
        row=conn.execute("SELECT status,attempts,result_json FROM integration_event_delivery WHERE event_id=?", (delivery_id,)).fetchone()
        if row and row["status"]=="completed":
            return {"status":"duplicate","event_id":delivery_id}
        if not row:
            conn.execute("INSERT INTO integration_event_delivery(event_id,event,payload_json,created_at,updated_at) VALUES(?,?,?,?,?)",
                         (delivery_id,event,json.dumps(payload,ensure_ascii=False,default=str),time.time(),time.time()))
        conn.commit()
    retry=max(0,int(cfg["payload"].get("retry",3)))
    attempts=0
    last_error=""
    while attempts<=retry:
        attempts+=1
        try:
            result=executor(action,payload)
            with connect() as conn:
                conn.execute("UPDATE integration_event_delivery SET status='completed',attempts=?,updated_at=?,error='' WHERE event_id=?",(attempts,time.time(),delivery_id)); conn.commit()
            return {"status":"dispatched","event_id":delivery_id,"attempts":attempts,"result":result,"timestamp":time.time()}
        except Exception as exc:
            last_error=str(exc)
    status="dead-letter" if bool(cfg["payload"].get("dead_letter",True)) else "failed"
    with connect() as conn:
        conn.execute("UPDATE integration_event_delivery SET status=?,attempts=?,updated_at=?,error=? WHERE event_id=?",(status,attempts,time.time(),last_error,delivery_id)); conn.commit()
    return {"status":status,"event_id":delivery_id,"attempts":attempts,"error":last_error}
