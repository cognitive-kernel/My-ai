"""Persistent event -> action mappings with idempotency metadata."""
from __future__ import annotations
import hashlib, json, time
from .control_plane import put_record, get_record

def register_event(event: str, action: dict, *, enabled=True, retry=3, dead_letter=True):
    return put_record("integrations.events",event,{"action":action,"retry":retry,"dead_letter":dead_letter},enabled=enabled)

def event_key(event: str, payload) -> str:
    return hashlib.sha256((event+"|"+json.dumps(payload,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()

def dispatch(event: str, payload, executor, *, event_id=None):
    cfg=get_record("integrations.events",event)
    if not cfg or not cfg.get("enabled"): return {"status":"ignored","reason":"event-disabled"}
    action=cfg["payload"].get("action",{})
    return {"status":"dispatched","event_id":event_id or event_key(event,payload),"result":executor(action,payload),"timestamp":time.time()}
