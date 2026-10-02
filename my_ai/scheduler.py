from __future__ import annotations

import json
import threading
import logging
import time
import uuid
from .learner import LearningEngine
from .platform import resource_status
from .curriculum import LANGUAGE_CURRICULA, canonical_language
from .db import connect, execute, fetch_all
from .dynamic_learning import due_domains
from .config import settings
from .resource_guard import limits as resource_limits
from .scheduler_resilience import mark_stale, record as record_scheduler_event

logger = logging.getLogger(__name__)

class StudyScheduler:
    def __init__(self, interval_seconds=None):
        self.interval_seconds=int(interval_seconds or settings.scheduler_interval_seconds); self._workers={}; self._review_stop=threading.Event(); self._monitor_thread=None
        self.language="Python"; self.last_result=None; self.current_topic=None; self.stage="idle"; self.error=None; self._lock=threading.RLock(); self._worker_slots=threading.BoundedSemaphore(max(1,settings.learning_max_concurrent_workers)); self._supervisor_stop=threading.Event(); self._supervisor_thread=None; self._lease_owner=uuid.uuid4().hex; self._lease_seconds=30.0
    def start_learning_supervisor(self):
        if self._supervisor_thread and self._supervisor_thread.is_alive(): return
        self._supervisor_stop.clear(); self._supervisor_thread=threading.Thread(target=self._supervisor_loop,daemon=True); self._supervisor_thread.start()
    def stop_learning_supervisor(self): self._supervisor_stop.set()
    def _supervisor_loop(self):
        while not self._supervisor_stop.is_set():
            try:
                mark_stale()
                for row in fetch_all("SELECT language,session_id,status FROM learning_workers WHERE status IN ('running','retrying')"):
                    language=str(row["language"] or "").strip(); key=language.casefold()
                    if language and not (self._workers.get(key) and self._workers[key][0].is_alive()):
                        record_scheduler_event(language,"worker_recovery",session_id=row["session_id"])
                        self.start(language,row["session_id"])
            except Exception: logger.exception("LEARNING_SUPERVISOR_FAILURE")
            self._supervisor_stop.wait(2)
    def start_review_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive(): return
        self._review_stop.clear(); self._monitor_thread=threading.Thread(target=self._review_loop,daemon=True); self._monitor_thread.start()
    def _normalize_language(self,language):
        language=str(language or "Python").strip() or "Python"; known=canonical_language(language); return known if known in LANGUAGE_CURRICULA else language
    def _ensure_lease_table(self): execute("CREATE TABLE IF NOT EXISTS learning_worker_leases (language TEXT PRIMARY KEY, owner TEXT NOT NULL, lease_until REAL NOT NULL)")
    def _acquire_lease(self,language):
        self._ensure_lease_table(); now=time.time(); until=now+self._lease_seconds
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE"); row=conn.execute("SELECT owner,lease_until FROM learning_worker_leases WHERE language=?",(language,)).fetchone()
            if row and float(row["lease_until"])>now and row["owner"]!=self._lease_owner: conn.rollback(); return False
            conn.execute("INSERT INTO learning_worker_leases(language,owner,lease_until) VALUES(?,?,?) ON CONFLICT(language) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until",(language,self._lease_owner,until)); conn.commit(); return True
    def _renew_lease(self,language):
        with connect() as conn:
            cur=conn.execute("UPDATE learning_worker_leases SET lease_until=? WHERE language=? AND owner=?",(time.time()+self._lease_seconds,language,self._lease_owner)); conn.commit(); return cur.rowcount==1
    def _release_lease(self,language):
        normalized=self._normalize_language(language)
        execute("DELETE FROM learning_worker_leases WHERE language=? AND owner=?",(normalized,self._lease_owner))
    def start(self,language="Python",session_id=None):
        language=self._normalize_language(language); key=language.casefold()
        with self._lock:
            existing=self._workers.get(key)
            if existing and existing[0].is_alive():
                return
        if not self._acquire_lease(language): return
        with self._lock:
            existing=self._workers.get(key)
            if existing and existing[0].is_alive():
                self._release_lease(language)
                return
            if session_id is None:
                rows=fetch_all("SELECT session_id FROM learning_workers WHERE lower(language)=? LIMIT 1",(key,)); session_id=rows[0]["session_id"] if rows else None
            stop_event=threading.Event(); thread=threading.Thread(target=self._loop,args=(language,stop_event),daemon=True,name=f"myai-learning-{language}"); self._workers[key]=(thread,stop_event); self.language=language; self.stage="starting"
            execute("""INSERT INTO learning_workers(language,session_id,status,stage,started_at,updated_at) VALUES(?,?,?,'starting',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT(language) DO UPDATE SET session_id=excluded.session_id,status='running',stage='starting',updated_at=CURRENT_TIMESTAMP""",(language,session_id,"running")); thread.start()
    def stop_learning(self,language=None):
        target=str(language).casefold() if language else None
        for key,(_,event) in list(self._workers.items()):
            if target and key!=target: continue
            event.set(); self._release_lease(key); execute("UPDATE learning_workers SET status='stopping',stage='stopping',updated_at=CURRENT_TIMESTAMP WHERE lower(language)=?",(key,))
        self.stage="stopping"
        record_scheduler_event(language or "all","stop_requested")
    def stop(self): self.stop_learning(); self.stop_review_monitor(); self.stop_learning_supervisor()
    def stop_review_monitor(self): self._review_stop.set()
    def running(self): return any(t.is_alive() for t,_ in self._workers.values())
    def status(self):
        rows=fetch_all("SELECT id,language,session_id,status,stage,current_topic,error,last_result,started_at,updated_at FROM learning_workers ORDER BY id"); workers=[]
        for row in rows:
            item=dict(row); item["running"]=bool(self._workers.get(str(item["language"]).casefold()) and self._workers[str(item["language"]).casefold()][0].is_alive()); workers.append(item)
        active=[x for x in workers if x["running"]]; primary=active[0] if active else (workers[-1] if workers else None)
        runtime = fetch_all("SELECT status,updated_at FROM learning_runtime WHERE id=1")
        return {
            "running": bool(active),
            "language": primary["language"] if primary else self.language,
            "stage": primary["stage"] if primary else self.stage,
            "current_topic": primary["current_topic"] if primary else self.current_topic,
            "last_result": primary.get("last_result") if primary else self.last_result,
            "error": primary.get("error") if primary else self.error,
            "interval_seconds": self.interval_seconds,
            "session_id": primary.get("session_id") if primary else None,
            "runtime_status": runtime[0]["status"] if runtime else "idle",
            "runtime_updated_at": runtime[0]["updated_at"] if runtime else None,
            "workers": workers,
            "active_workers": active,
            "resources": {**resource_status(), **resource_limits()},
        }
    @staticmethod
    def _wait_for_resources(stop_event):
        while not stop_event.is_set():
            limits = resource_limits(); cpu=float(limits["cpu_percent"]); ram=float(limits["ram_percent"]); r=resource_status()
            if r.get("cpu_percent") is None or r.get("ram_percent") is None or (r.get("cpu_percent")<=cpu and r.get("ram_percent")<=ram): return r
            stop_event.wait(1)
        raise InterruptedError("learning stopped")
    def _update_worker(self,language,stage,topic=None,result=None,error=None,status=None):
        updates=["stage=?","updated_at=CURRENT_TIMESTAMP"]; params=[stage]
        if topic is not None: updates.append("current_topic=?"); params.append(topic)
        if result is not None: updates.append("last_result=?"); params.append(json.dumps(result,ensure_ascii=False,default=str))
        if error is not None: updates.append("error=?"); params.append(error)
        if status is not None: updates.append("status=?"); params.append(status)
        params.append(language); execute(f"UPDATE learning_workers SET {', '.join(updates)} WHERE language=?",tuple(params)); self.stage=stage; self.current_topic=topic or self.current_topic
    def _domain_complete(self,language):
        topics=LANGUAGE_CURRICULA.get(language,[]); completed={str(r["topic"]) for r in fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'",(language,))}; return bool(topics) and {str(x["topic"]) for x in topics}.issubset(completed)
    def _review_loop(self):
        while not self._review_stop.is_set():
            try:
                for name in due_domains():
                    if str(name).startswith("custom_course:"): continue
                    self.last_result={"status":"weekly_review","language":name}
            except Exception as exc: logger.exception("LEARNING_REVIEW_FAILURE: %s",exc)
            self._review_stop.wait(min(self.interval_seconds,3600))
    def _schedule_worker_recovery(self, language, stop_event):
        if stop_event.is_set():
            return
        rows = fetch_all("SELECT session_id FROM learning_workers WHERE lower(language)=? LIMIT 1", (str(language).casefold(),))
        session_id = rows[0]["session_id"] if rows else None
        def recover():
            if not stop_event.is_set():
                self.start(language, session_id)
        timer = threading.Timer(1.0, recover)
        timer.daemon = True
        timer.start()

    def _loop(self,language,stop_event):
        if not self._renew_lease(language): return
        engine=LearningEngine(); errors=0
        try:
            while not stop_event.is_set():
                try:
                    self._renew_lease(language)
                    self._wait_for_resources(stop_event)
                    acquired=self._worker_slots.acquire(timeout=max(1.0,float(getattr(settings,"resource_wait_seconds",30))))
                    if not acquired:
                        raise TimeoutError("learning worker concurrency limit reached")
                    try:
                        result=engine.learn_next(language,progress_callback=lambda stage,topic=None:self._update_worker(language,stage,topic),stop_event=stop_event)
                    finally:
                        self._worker_slots.release()
                    errors=0; self._update_worker(language,self.stage,result=result,status="running")
                    if result.get("status")=="complete": self._update_worker(language,"completed",result=result,status="completed"); break
                    if stop_event.wait(min(self.interval_seconds,60)): break
                except InterruptedError: break
                except Exception as exc:
                    errors += 1
                    logger.exception("LEARNING_FAILURE: %s", exc)
                    max_retries = max(1, int(getattr(settings, "learning_max_retries", 5)))
                    terminal = errors >= max_retries
                    status = "failed" if terminal else "retrying"
                    self._update_worker(
                        language,
                        status,
                        result={"status": "error", "error": str(exc), "consecutive_errors": errors, "max_retries": max_retries},
                        error=str(exc),
                        status=status,
                    )
                    record_scheduler_event(language, "worker_failure", error=str(exc), consecutive_errors=errors, max_retries=max_retries, terminal=terminal)
                    if terminal or stop_event.wait(min(60, 2 ** min(errors, 5))): break
        finally:
            self._release_lease(language); self._workers.pop(language.casefold(),None)
