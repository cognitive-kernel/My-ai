from __future__ import annotations

import json
import threading
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from .learner import LearningEngine
from .platform import resource_status
from .curriculum import LANGUAGE_CURRICULA, LANGUAGE_SOURCES, canonical_language
from .db import connect, execute, fetch_all
from .dynamic_learning import REVIEW_DAYS, ensure_domain, due_domains, weekly_review, review_history
from .config import settings
from .settings_store import get_setting
from .resource_guard import limits as resource_limits
from .learning_sources import find_unlearned_new_sources

logger = logging.getLogger(__name__)


class StudyScheduler:
    def __init__(self, interval_seconds=None):
        self.interval_seconds = int(interval_seconds or settings.scheduler_interval_seconds)
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._review_stop = threading.Event(); self._monitor_thread = None
        self.language = "Python"; self.last_result = None; self.current_topic = None; self.stage = "idle"; self.error = None
        self._lock = threading.RLock(); self._worker_slots = threading.BoundedSemaphore(max(1, settings.learning_max_concurrent_workers))
        self._restart_lock = threading.Lock(); self._supervisor_stop = threading.Event(); self._supervisor_thread = None
        self._lease_owner = uuid.uuid4().hex; self._lease_seconds = 30.0

    def start_learning_supervisor(self):
        if self._supervisor_thread and self._supervisor_thread.is_alive(): return
        self._supervisor_stop.clear(); self._supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True, name="myai-learning-supervisor"); self._supervisor_thread.start()

    def stop_learning_supervisor(self): self._supervisor_stop.set()

    def _supervisor_loop(self):
        while not self._supervisor_stop.is_set():
            try:
                rows = fetch_all("SELECT language,session_id,status FROM learning_workers WHERE status IN ('running','retrying')")
                for row in rows:
                    language = str(row["language"] or "").strip()
                    if not language: continue
                    key = language.casefold()
                    with self._lock:
                        owned = self._workers.get(key); alive = bool(owned and owned[0].is_alive())
                    if not alive:
                        logger.warning("LEARNING_SUPERVISOR_RESTART: language=%s session_id=%s status=%s", language, row["session_id"], row["status"])
                        self.start(language, row["session_id"])
            except Exception:
                logger.exception("LEARNING_SUPERVISOR_FAILURE")
            self._supervisor_stop.wait(2.0)

    def start_review_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive(): return
        self._review_stop.clear(); self._monitor_thread = threading.Thread(target=self._review_loop, daemon=True, name="myai-weekly-review"); self._monitor_thread.start()

    def _normalize_language(self, language):
        language = str(language or "Python").strip() or "Python"; known = canonical_language(language)
        return known if known in LANGUAGE_CURRICULA else language

    def _ensure_lease_table(self):
        execute("CREATE TABLE IF NOT EXISTS learning_worker_leases (language TEXT PRIMARY KEY, owner TEXT NOT NULL, lease_until REAL NOT NULL)")

    def _acquire_lease(self, language):
        self._ensure_lease_table(); now = time.time(); lease_until = now + self._lease_seconds
        # BEGIN IMMEDIATE serializes the check-and-acquire operation across
        # scheduler instances/processes; SELECT followed by UPSERT was racy.
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT owner,lease_until FROM learning_worker_leases WHERE language=?", (language,)).fetchone()
                if row and float(row["lease_until"]) > now and row["owner"] != self._lease_owner:
                    conn.rollback(); return False
                conn.execute("INSERT INTO learning_worker_leases(language,owner,lease_until) VALUES(?,?,?) ON CONFLICT(language) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until", (language, self._lease_owner, lease_until))
                conn.commit(); return True
            except Exception:
                conn.rollback(); raise

    def _renew_lease(self, language):
        with connect() as conn:
            cursor = conn.execute("UPDATE learning_worker_leases SET lease_until=? WHERE language=? AND owner=?", (time.time() + self._lease_seconds, language, self._lease_owner)); conn.commit(); return cursor.rowcount == 1

    def _release_lease(self, language): execute("DELETE FROM learning_worker_leases WHERE language=? AND owner=?", (language, self._lease_owner))

    def start(self, language="Python", session_id=None):
        language = self._normalize_language(language); key = language.casefold()
        if not self._acquire_lease(language): logger.info("LEARNING_WORKER_LEASE_HELD: language=%s", language); return
        with self._lock:
            existing = self._workers.get(key)
            if session_id is None:
                persisted = fetch_all("SELECT session_id FROM learning_workers WHERE lower(language)=? LIMIT 1", (key,))
                if persisted: session_id = persisted[0]["session_id"]
            if session_id:
                try:
                    execute("UPDATE learning_sessions SET status='started',phase=CASE WHEN phase='completed' THEN 'starting' ELSE phase END WHERE id=? AND status!='completed'", (session_id,))
                except Exception as exc: logger.warning("LEARNING_SESSION_RESUME_STATE_UPDATE_FAILED: %s", exc)
            if existing and existing[0].is_alive():
                existing[1].clear(); execute("UPDATE learning_workers SET session_id=?,status='running',stage='starting',updated_at=CURRENT_TIMESTAMP WHERE language=?", (session_id, language)); return
            worker_stop = threading.Event(); thread = threading.Thread(target=self._loop, args=(language, worker_stop), daemon=True, name=f"myai-learning-{language}")
            self._workers[key] = (thread, worker_stop); self.language = language; self.stage = "starting"; self.current_topic = None; self.last_result = None; self.error = None
            current_topic = None
            if session_id:
                rows = fetch_all("SELECT topic FROM learning_sessions WHERE id=?", (session_id,)); current_topic = rows[0]["topic"] if rows else None
            try: execute("UPDATE learning_domains SET auto_learn=1 WHERE lower(name)=?", (key,))
            except Exception as exc: logger.warning("SILENT_FAILURE_REPLACED: %s", exc)
            execute("""INSERT INTO learning_workers(language,session_id,status,stage,current_topic,started_at,updated_at) VALUES(?,?,?,'starting',?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT(language) DO UPDATE SET session_id=excluded.session_id,status='running',stage='starting',current_topic=excluded.current_topic,error=NULL,last_result=NULL,started_at=excluded.started_at,updated_at=CURRENT_TIMESTAMP""", (language, session_id, "running", current_topic))
            execute("""INSERT INTO learning_runtime(id,language,session_id,status,started_at,updated_at) VALUES(1,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET language=excluded.language,session_id=excluded.session_id,status=excluded.status,started_at=excluded.started_at,updated_at=CURRENT_TIMESTAMP""", (language, session_id, "running")); thread.start()

    def stop_learning(self, language=None):
        target = str(language).strip().casefold() if language else None
        with self._lock:
            for key, (thread, stop_event) in list(self._workers.items()):
                if target is not None and key != target: continue
                stop_event.set(); execute("UPDATE learning_workers SET status='stopping',stage='stopping',updated_at=CURRENT_TIMESTAMP WHERE lower(language)=?", (key,))
                try: execute("UPDATE learning_domains SET auto_learn=0 WHERE lower(name)=?", (key,))
                except Exception as exc: logger.warning("SILENT_FAILURE_REPLACED: %s", exc)
                self._release_lease(key)
            execute("UPDATE learning_runtime SET status='stopping',updated_at=CURRENT_TIMESTAMP WHERE id=1")
        self.stage = "stopping"

    def stop(self): self.stop_learning(); self.stop_review_monitor(); self.stop_learning_supervisor()
    def stop_review_monitor(self): self._review_stop.set()
    def running(self): return any(thread.is_alive() for thread, _ in self._workers.values())

    def status(self):
        with self._lock:
            rows = fetch_all("SELECT id,language,session_id,status,stage,current_topic,error,last_result,started_at,updated_at FROM learning_workers ORDER BY id"); workers=[]
            for row in rows:
                item=dict(row)
                try: item["last_result"]=json.loads(item["last_result"]) if item["last_result"] else None
                except (TypeError,ValueError): item["last_result"]=None
                owned=getattr(self,"_workers",{}).get(str(item["language"]).casefold()); item["running"]=bool(owned and owned[0].is_alive()); workers.append(item)
            active=[x for x in workers if x["running"]]; primary=active[0] if active else (workers[-1] if workers else None); live=resource_status(); cfg=resource_limits()
            return {"running":bool(active),"language":primary["language"] if primary else self.language,"stage":primary["stage"] if primary else self.stage,"current_topic":primary["current_topic"] if primary else self.current_topic,"last_result":primary["last_result"] if primary else self.last_result,"error":primary["error"] if primary else self.error,"interval_seconds":self.interval_seconds,"session_id":primary["session_id"] if primary else None,"runtime_status":"running" if active else (primary["status"] if primary else "idle"),"runtime_updated_at":primary["updated_at"] if primary else None,"workers":workers,"active_workers":active,"resources":{**live,**cfg},"weekly_review":{"due_domains":due_domains(),"next_reviews":fetch_all("SELECT name,next_review_at FROM learning_domains WHERE next_review_at IS NOT NULL AND name NOT LIKE 'custom_course:%' ORDER BY next_review_at"),"monitor_running":bool(getattr(self,"_monitor_thread",None) and self._monitor_thread.is_alive()),"history":review_history(10)}}

    @staticmethod
    def _wait_for_resources(stop_event):
        while not stop_event.is_set():
            try: cpu_limit=float(get_setting("resources.cpu_percent",str(settings.scheduler_max_cpu_percent))); ram_limit=float(get_setting("resources.ram_percent",str(settings.scheduler_max_ram_percent)))
            except (TypeError,ValueError): cpu_limit=float(settings.scheduler_max_cpu_percent); ram_limit=float(settings.scheduler_max_ram_percent)
            resources=resource_status(); cpu=resources.get("cpu_percent"); ram=resources.get("ram_percent")
            if cpu is None or ram is None or (cpu<=cpu_limit and (ram is None or ram<=ram_limit)): return resources
            stop_event.wait(1.0)
        raise InterruptedError("learning stopped")

    def _update_worker(self, language, stage, topic=None, result=None, error=None, status=None):
        with self._lock:
            updates=["stage=?","updated_at=CURRENT_TIMESTAMP"]; params=[stage]
            if topic is not None: updates.append("current_topic=?"); params.append(topic)
            if result is not None: updates.append("last_result=?"); params.append(json.dumps(result,ensure_ascii=False,default=str))
            if error is not None: updates.append("error=?"); params.append(error)
            if status is not None: updates.append("status=?"); params.append(status)
            params.append(language); execute(f"UPDATE learning_workers SET {', '.join(updates)} WHERE language=?",tuple(params)); self.language=language; self.stage=stage
            if topic: self.current_topic=topic
            if result is not None: self.last_result=result
            if error is not None: self.error=error

    def update_progress(self, stage, topic=None): self.stage=stage; self.current_topic=topic if topic else self.current_topic

    @staticmethod
    def _latest_learning_message():
        rows=fetch_all("SELECT c.content FROM conversations c JOIN chat_sessions s ON s.id=c.session_id WHERE c.role='user' AND s.kind='learning' ORDER BY c.id DESC LIMIT 1"); return str(rows[0]["content"]) if rows else ""

    @staticmethod
    def _schedule_review(language):
        language=canonical_language(language); topics=LANGUAGE_CURRICULA.get(language,[]); sources=LANGUAGE_SOURCES.get(language,[])
        if not topics: return None
        ensure_domain(language, topics, sources); return language
