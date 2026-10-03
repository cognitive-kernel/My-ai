from __future__ import annotations

import json
import threading
import logging
import time
import uuid
from pathlib import Path
from .learner import LearningEngine
from .platform import resource_status
from .curriculum import LANGUAGE_CURRICULA, canonical_language
from .db import connect, execute, fetch_all
from .infra.persistence import purge_expired_knowledge
from .dynamic_learning import due_domains
from .config import settings
from .settings_store import get_setting
from .resource_guard import limits as resource_limits
from .backup_manager import backup as backup_database, prune_backups

logger = logging.getLogger(__name__)

class StudyScheduler:
    def __init__(self, interval_seconds=None):
        self.interval_seconds=int(interval_seconds or settings.scheduler_interval_seconds); self._workers={}; self._review_stop=threading.Event(); self._monitor_thread=None
        self.language="Python"; self.last_result=None; self.current_topic=None; self.stage="idle"; self.error=None; self._lock=threading.RLock(); self._worker_slots=threading.BoundedSemaphore(max(1,int(get_setting("scheduler.concurrency",settings.learning_max_concurrent_workers)))) ; self._supervisor_stop=threading.Event(); self._supervisor_thread=None; self._lease_owner=uuid.uuid4().hex; self._lease_seconds=30.0; self._backup_stop=threading.Event(); self._backup_thread=None; self._backup_last_run=0.0
    def start_backup_scheduler(self):
        if self._backup_thread and self._backup_thread.is_alive(): return
        self._backup_stop.clear(); self._backup_thread=threading.Thread(target=self._backup_loop,daemon=True,name="myai-backup-scheduler"); self._backup_thread.start()
    def stop_backup_scheduler(self):
        self._backup_stop.set()
        if self._backup_thread and self._backup_thread is not threading.current_thread(): self._backup_thread.join(timeout=2.0)
    @staticmethod
    def _backup_interval_seconds(schedule):
        value=str(schedule or "manual").strip().lower()
        if value in {"manual","off","disabled","none"}: return None
        if value in {"hourly","1h"}: return 3600.0
        if value in {"daily","1d"}: return 86400.0
        if value in {"weekly","1w"}: return 604800.0
        if value.startswith("every:"):
            try: return max(60.0, float(value.split(":",1)[1]))
            except ValueError: return None
        return None
    def run_scheduled_backup_once(self):
        destination=str(get_setting("database.backup_destination","") or "").strip() or "data/backups"
        retention=max(1,int(get_setting("database.backup_retention",14)))
        Path(destination).mkdir(parents=True,exist_ok=True)
        stamp=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())
        target=Path(destination)/f"my_ai-{stamp}.db"
        result=backup_database(str(target))
        prune_backups(destination,retention)
        self._backup_last_run=time.time()
        return result
    def _backup_loop(self):
        while not self._backup_stop.is_set():
            interval=self._backup_interval_seconds(get_setting("database.backup_schedule","daily"))
            if interval is None:
                self._backup_stop.wait(60); continue
            elapsed=time.time()-self._backup_last_run
            if elapsed >= interval:
                try: self.run_scheduled_backup_once()
                except Exception: logger.exception("DATABASE_BACKUP_FAILURE")
                self._backup_stop.wait(1)
            else:
                self._backup_stop.wait(min(60.0,max(1.0,interval-elapsed)))

    def start_learning_supervisor(self):
        if self._supervisor_thread and self._supervisor_thread.is_alive(): return
        self._supervisor_stop.clear(); self._supervisor_thread=threading.Thread(target=self._supervisor_loop,daemon=True); self._supervisor_thread.start()
    def stop_learning_supervisor(self): self._supervisor_stop.set()
    def _supervisor_loop(self):
        while not self._supervisor_stop.is_set():
            try:
                for row in fetch_all("SELECT language,session_id,status FROM learning_workers WHERE status IN ('running','retrying')"):
                    language=str(row["language"] or "").strip(); key=language.casefold()
                    if language and not (self._workers.get(key) and self._workers[key][0].is_alive()): self.start(language,row["session_id"])
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
    def _ensure_worker_tables(self):
        execute("CREATE TABLE IF NOT EXISTS learning_workers (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL UNIQUE, session_id INTEGER, status TEXT NOT NULL DEFAULT 'idle', stage TEXT NOT NULL DEFAULT 'idle', current_topic TEXT, error TEXT, last_result TEXT, started_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        self._ensure_lease_table()

    def _schedule_worker_recovery(self, language, stop_event):
        if stop_event.is_set():
            return
        backoff = max(0.0, float(get_setting("scheduler.retry_backoff", 5)))
        delay = min(60.0, max(0.0, backoff * (2 ** min(8, int(getattr(settings, "learning_max_retries", 3))))))
        def recover():
            if stop_event.is_set():
                return
            rows = fetch_all("SELECT session_id,status FROM learning_workers WHERE lower(language)=? LIMIT 1", (str(language).casefold(),))
            self.start(language, rows[0]["session_id"] if rows else None)
        timer = threading.Timer(delay, recover)
        timer.daemon = True
        timer.start()

    def start(self,language="Python",session_id=None):
        self._ensure_worker_tables()
        language=self._normalize_language(language); key=language.casefold()
        max_workers=max(1,int(get_setting("scheduler.worker_count", 2)))
        with self._lock:
            active_count=sum(1 for thread,_event in self._workers.values() if thread.is_alive())
            if active_count >= max_workers and key not in self._workers:
                logger.info("Scheduler worker limit reached: %s", max_workers)
                return
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
        selected=[]
        for key,(thread,event) in list(self._workers.items()):
            if target and key!=target: continue
            event.set()
            self._release_lease(key)
            execute("UPDATE learning_workers SET status='stopping',stage='stopping',updated_at=CURRENT_TIMESTAMP WHERE lower(language)=?",(key,))
            selected.append((key,thread))
        for key,thread in selected:
            if thread is not threading.current_thread():
                thread.join(timeout=2.0)
            if not thread.is_alive():
                with self._lock:
                    self._workers.pop(key, None)
        self.stage="stopping"
    def stop(self):
        self.stop_learning()
        self.stop_review_monitor()
        self.stop_learning_supervisor()
        self.stop_backup_scheduler()
        if self._monitor_thread and self._monitor_thread is not threading.current_thread():
            self._monitor_thread.join(timeout=2.0)
        if self._supervisor_thread and self._supervisor_thread is not threading.current_thread():
            self._supervisor_thread.join(timeout=2.0)
    def stop_review_monitor(self): self._review_stop.set()
    def running(self): return any(t.is_alive() for t,_ in self._workers.values())
    def status(self):
        rows=fetch_all("SELECT id,language,session_id,status,stage,current_topic,error,last_result,started_at,updated_at FROM learning_workers ORDER BY id"); workers=[]
        for row in rows:
            item=dict(row); item["running"]=bool(self._workers.get(str(item["language"]).casefold()) and self._workers[str(item["language"]).casefold()][0].is_alive()); workers.append(item)
        active=[x for x in workers if x["running"]]; primary=active[0] if active else (workers[-1] if workers else None)
        return {"running":bool(active),"language":primary["language"] if primary else self.language,"stage":primary["stage"] if primary else self.stage,"current_topic":primary["current_topic"] if primary else self.current_topic,"last_result":json.loads(primary["last_result"]) if primary and primary.get("last_result") else self.last_result,"error":primary.get("error") if primary else self.error,"interval_seconds":self.interval_seconds,"session_id":primary.get("session_id") if primary else None,"runtime_status":primary.get("status") if primary else "idle","runtime_updated_at":primary.get("updated_at") if primary else None,"workers":workers,"active_workers":active,"resources":{**resource_status(),**resource_limits()}}
    @staticmethod
    def _wait_for_resources(stop_event):
        while not stop_event.is_set():
            cpu=float(get_setting("resources.cpu_percent",str(settings.scheduler_max_cpu_percent))); ram=float(get_setting("resources.ram_percent",str(settings.scheduler_max_ram_percent))); r=resource_status()
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
    def _loop(self,language,stop_event):
        self._ensure_worker_tables()
        if not self._renew_lease(language) and not self._acquire_lease(language): return
        engine=LearningEngine(); errors=0
        try:
            while not stop_event.is_set():
                try:
                    purge_expired_knowledge()
                except Exception:
                    logger.exception("MEMORY_RETENTION_CLEANUP_FAILURE")
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
                    errors+=1; logger.exception("LEARNING_FAILURE: %s",exc); self._update_worker(language,"retrying",result={"status":"error","error":str(exc),"consecutive_errors":errors},error=str(exc),status="retrying"); self._schedule_worker_recovery(language, stop_event)
                    if stop_event.wait(min(60,2**min(errors,5))): break
        finally:
            self._release_lease(language); self._workers.pop(language.casefold(),None)
