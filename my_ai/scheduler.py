from __future__ import annotations

import json
import threading
import logging
from datetime import datetime, timedelta, timezone

from .learner import LearningEngine
from .platform import resource_status
from .curriculum import LANGUAGE_CURRICULA, LANGUAGE_SOURCES, canonical_language
from .db import execute, fetch_all
from .domain_registry import load_saved_domains
from .dynamic_learning import REVIEW_DAYS, ensure_domain, resolve_learning_target, due_domains, weekly_review, review_history
from .config import settings
from .settings_store import get_setting
from .resource_guard import limits as resource_limits
from .learning_sources import find_unlearned_new_sources

logger = logging.getLogger(__name__)


class StudyScheduler:
    def __init__(self, interval_seconds=None):
        self.interval_seconds = int(interval_seconds or settings.scheduler_interval_seconds)
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._review_stop = threading.Event()
        self._monitor_thread = None
        self.language = "Python"
        self.last_result = None
        self.current_topic = None
        self.stage = "idle"
        self.error = None
        self._lock = threading.RLock()
        self._worker_slots = threading.BoundedSemaphore(max(1, settings.learning_max_concurrent_workers))
        self._restart_lock = threading.Lock()
        self._supervisor_stop = threading.Event()
        self._supervisor_thread = None
        try:
            load_saved_domains()
        except Exception as exc:
            self.error = str(exc)

    def start_learning_supervisor(self):
        if self._supervisor_thread and self._supervisor_thread.is_alive():
            return
        self._supervisor_stop.clear()
        self._supervisor_thread = threading.Thread(
            target=self._supervisor_loop, daemon=True, name="myai-learning-supervisor"
        )
        self._supervisor_thread.start()

    def stop_learning_supervisor(self):
        self._supervisor_stop.set()

    def _supervisor_loop(self):
        while not self._supervisor_stop.is_set():
            try:
                rows = fetch_all(
                    "SELECT language,session_id,status FROM learning_workers WHERE status IN ('running','retrying')"
                )
                for row in rows:
                    language = str(row["language"] or "").strip()
                    if not language:
                        continue
                    key = language.casefold()
                    with self._lock:
                        owned = self._workers.get(key)
                        alive = bool(owned and owned[0].is_alive())
                    if not alive:
                        logger.warning(
                            "LEARNING_SUPERVISOR_RESTART: language=%s session_id=%s status=%s",
                            language, row["session_id"], row["status"],
                        )
                        self.start(language, row["session_id"])
            except Exception:
                logger.exception("LEARNING_SUPERVISOR_FAILURE")
            self._supervisor_stop.wait(2.0)

    def start_review_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._review_stop.clear()
        self._monitor_thread = threading.Thread(target=self._review_loop, daemon=True, name="myai-weekly-review")
        self._monitor_thread.start()

    def _normalize_language(self, language):
        language = str(language or "Python").strip() or "Python"
        known = canonical_language(language)
        if known in LANGUAGE_CURRICULA:
            return known
        return resolve_learning_target(self._latest_learning_message(), language)

    def start(self, language="Python", session_id=None):
        language = self._normalize_language(language)
        key = language.casefold()
        with self._lock:
            existing = self._workers.get(key)
            if existing and existing[0].is_alive():
                # Resume must clear the cancellation flag. Otherwise a worker that
                # was stopped just before Resume will exit immediately.
                existing[1].clear()
                if session_id:
                    execute("UPDATE learning_workers SET session_id=?,status='running',stage='starting',updated_at=CURRENT_TIMESTAMP WHERE language=?", (session_id, language))
                else:
                    execute("UPDATE learning_workers SET status='running',stage='starting',updated_at=CURRENT_TIMESTAMP WHERE language=?", (language,))
                try:
                    execute("UPDATE learning_domains SET auto_learn=1 WHERE lower(name)=?", (key,))
                except Exception:
                    pass
                return
            worker_stop = threading.Event()
            thread = threading.Thread(
                target=self._loop,
                args=(language, worker_stop),
                daemon=True,
                name=f"myai-learning-{language}",
            )
            self._workers[key] = (thread, worker_stop)
            self.language = language
            self.stage = "starting"
            self.current_topic = None
            self.last_result = None
            self.error = None
            current_topic = None
            if session_id:
                rows = fetch_all("SELECT topic FROM learning_sessions WHERE id=?", (session_id,))
                if rows:
                    current_topic = rows[0]["topic"]
            try:
                execute("UPDATE learning_domains SET auto_learn=1 WHERE lower(name)=?", (key,))
            except Exception:
                pass
            execute(
                """INSERT INTO learning_workers(language,session_id,status,stage,current_topic,started_at,updated_at)
                   VALUES(?,?,?,'starting',?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                   ON CONFLICT(language) DO UPDATE SET
                   session_id=excluded.session_id,status='running',stage='starting',
                   current_topic=excluded.current_topic,error=NULL,last_result=NULL,
                   started_at=excluded.started_at,updated_at=CURRENT_TIMESTAMP""",
                (language, session_id, "running", current_topic),
            )
            execute(
                """INSERT INTO learning_runtime(id,language,session_id,status,started_at,updated_at)
                   VALUES(1,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                   ON CONFLICT(id) DO UPDATE SET language=excluded.language,session_id=excluded.session_id,
                   status=excluded.status,started_at=excluded.started_at,updated_at=CURRENT_TIMESTAMP""",
                (language, session_id, "running"),
            )
            thread.start()

    def stop_learning(self, language=None):
        target = str(language).strip().casefold() if language else None
        with self._lock:
            for key, (thread, stop_event) in list(self._workers.items()):
                if target is not None and key != target:
                    continue
                stop_event.set()
                lang = key
                execute("UPDATE learning_workers SET status='stopping',stage='stopping',updated_at=CURRENT_TIMESTAMP WHERE lower(language)=?", (lang,))
                execute("CREATE TABLE IF NOT EXISTS learning_domains (name TEXT PRIMARY KEY, topics_json TEXT NOT NULL, sources_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_review_at TEXT, next_review_at TEXT, auto_learn INTEGER NOT NULL DEFAULT 1)")
                try:
                    execute("UPDATE learning_domains SET auto_learn=0 WHERE lower(name)=?", (lang,))
                except Exception:
                    pass
            execute("UPDATE learning_runtime SET status='stopping',updated_at=CURRENT_TIMESTAMP WHERE id=1")
        self.stage = "stopping"

    def stop(self):
        self.stop_learning()
        self.stop_review_monitor()
        self.stop_learning_supervisor()

    def stop_review_monitor(self):
        self._review_stop.set()

    def running(self):
        return any(thread.is_alive() for thread, _ in self._workers.values())

    def status(self):
        with self._lock:
            rows = fetch_all(
                """SELECT id,language,session_id,status,stage,current_topic,error,last_result,started_at,updated_at
                   FROM learning_workers ORDER BY id"""
            )
            workers = []
            for row in rows:
                item = dict(row)
                try:
                    item["last_result"] = json.loads(item["last_result"]) if item["last_result"] else None
                except (TypeError, ValueError):
                    item["last_result"] = None
                item["running"] = bool(
                    getattr(self, "_workers", {}).get(str(item["language"]).casefold())
                    and getattr(self, "_workers", {}).get(str(item["language"]).casefold())[0].is_alive()
                )
                workers.append(item)
            # Only workers owned by this scheduler instance are live. Persisted
            # rows from a previous process must remain visible in `workers`, but
            # must not be counted as active workers after a restart.
            active = [x for x in workers if x["running"]]
            primary = active[0] if active else (workers[-1] if workers else None)
            live = resource_status()
            cfg = resource_limits()
            return {
                "running": bool(active),
                "language": primary["language"] if primary else self.language,
                "stage": primary["stage"] if primary else self.stage,
                "current_topic": primary["current_topic"] if primary else self.current_topic,
                "last_result": primary["last_result"] if primary else self.last_result,
                "error": primary["error"] if primary else self.error,
                "interval_seconds": self.interval_seconds,
                "session_id": primary["session_id"] if primary else None,
                "runtime_status": "running" if active else (primary["status"] if primary else "idle"),
                "runtime_updated_at": primary["updated_at"] if primary else None,
                "workers": workers,
                "active_workers": active,
                "resources": {**live, **cfg},
                "weekly_review": {
                    "due_domains": due_domains(),
                    "next_reviews": fetch_all("SELECT name,next_review_at FROM learning_domains WHERE next_review_at IS NOT NULL AND name NOT LIKE 'custom_course:%' ORDER BY next_review_at"),
                    "monitor_running": bool(getattr(self, "_monitor_thread", None) and self._monitor_thread.is_alive()),
                    "history": review_history(10),
                },
            }

    @staticmethod
    def _wait_for_resources(stop_event):
        while not stop_event.is_set():
            try:
                cpu_limit = float(get_setting("resources.cpu_percent", str(settings.scheduler_max_cpu_percent)))
                ram_limit = float(get_setting("resources.ram_percent", str(settings.scheduler_max_ram_percent)))
            except (TypeError, ValueError):
                cpu_limit = float(settings.scheduler_max_cpu_percent)
                ram_limit = float(settings.scheduler_max_ram_percent)
            resources = resource_status()
            cpu = resources.get("cpu_percent")
            ram = resources.get("ram_percent")
            if cpu is None or ram is None or (cpu <= cpu_limit and (ram is None or ram <= ram_limit)):
                return resources
            stop_event.wait(1.0)
        raise InterruptedError("learning stopped")

    def _update_worker(self, language, stage, topic=None, result=None, error=None, status=None):
        with self._lock:
            updates = ["stage=?", "updated_at=CURRENT_TIMESTAMP"]
            params = [stage]
            if topic is not None:
                updates.append("current_topic=?")
                params.append(topic)
            if result is not None:
                updates.append("last_result=?")
                params.append(json.dumps(result, ensure_ascii=False, default=str))
            if error is not None:
                updates.append("error=?")
                params.append(error)
            if status is not None:
                updates.append("status=?")
                params.append(status)
            params.append(language)
            execute(f"UPDATE learning_workers SET {', '.join(updates)} WHERE language=?", tuple(params))
            self.language = language
            self.stage = stage
            if topic:
                self.current_topic = topic
            if result is not None:
                self.last_result = result
            if error is not None:
                self.error = error

    def update_progress(self, stage, topic=None):
        self.stage = stage
        if topic:
            self.current_topic = topic

    @staticmethod
    def _latest_learning_message():
        rows = fetch_all(
            """SELECT c.content FROM conversations c
               JOIN chat_sessions s ON s.id=c.session_id
               WHERE c.role='user' AND s.kind='learning'
               ORDER BY c.id DESC LIMIT 1"""
        )
        return str(rows[0]["content"]) if rows else ""

    @staticmethod
    def _schedule_review(language):
        language = canonical_language(language)
        topics = LANGUAGE_CURRICULA.get(language, [])
        sources = LANGUAGE_SOURCES.get(language, [])
        if not topics:
            return
        now = datetime.now(timezone.utc)
        next_review = (now + timedelta(days=REVIEW_DAYS)).isoformat()
        execute(
            """CREATE TABLE IF NOT EXISTS learning_domains (
                name TEXT PRIMARY KEY, topics_json TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_review_at TEXT, next_review_at TEXT,
                auto_learn INTEGER NOT NULL DEFAULT 1
            )"""
        )
        try:
            execute("ALTER TABLE learning_domains ADD COLUMN auto_learn INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
        execute(
            """INSERT INTO learning_domains(name,topics_json,sources_json,next_review_at)
               VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET
               topics_json=excluded.topics_json,sources_json=excluded.sources_json,
               updated_at=CURRENT_TIMESTAMP,
               next_review_at=COALESCE(learning_domains.next_review_at,excluded.next_review_at)""",
            (language, json.dumps(topics, ensure_ascii=False), json.dumps(sources, ensure_ascii=False), next_review),
        )

    @staticmethod
    def _domain_complete(language):
        topics = LANGUAGE_CURRICULA.get(language, [])
        if not topics:
            return False
        names = {str(x["topic"]) for x in topics}
        rows = fetch_all("SELECT topic,status FROM learning_sessions WHERE language=? AND status='completed'", (language,))
        return names.issubset({str(r["topic"]) for r in rows})

    def _queue_new_source_learning(self, language):
        pending = find_unlearned_new_sources(language)
        if not pending:
            return []
        topics = []
        seen = set()
        for item in pending:
            topic = str(item["topic"])
            if topic.casefold() in seen:
                continue
            seen.add(topic.casefold())
            topics.append(topic)
        completed = {str(r["topic"]) for r in fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'", (language,))}
        queued = []
        for topic in topics:
            if topic not in completed:
                continue
            active = fetch_all("SELECT id FROM learning_sessions WHERE language=? AND topic=? AND status='started' LIMIT 1", (language, topic))
            if active:
                continue
            goal = next((x.get("goal","") for x in LANGUAGE_CURRICULA.get(language, []) if x.get("topic")==topic), "")
            execute("INSERT INTO learning_sessions(language,topic,status,notes,progress_percent,phase) VALUES(?,?,?,?,?,?)",
                    (language, topic, "started", json.dumps({"topic":topic,"goal":goal}, ensure_ascii=False), 0.0, "new_source"))
            queued.append(topic)
        return queued

    def _custom_course_due(self):
        try:
            from .settings_feature import _course, _workers, _running
            rows = fetch_all(
                "SELECT c.id,c.name,d.next_review_at FROM custom_courses c "
                "JOIN learning_domains d ON d.name=('custom_course:' || c.id) "
                "WHERE c.active=1 AND d.next_review_at IS NOT NULL"
            )
            now = datetime.now(timezone.utc)
            due = []
            for row in rows:
                try:
                    when = datetime.fromisoformat(str(row["next_review_at"]).replace("Z", "+00:00"))
                    if when <= now:
                        due.append((int(row["id"]), str(row["name"])))
                except ValueError:
                    due.append((int(row["id"]), str(row["name"])))
            return due
        except Exception:
            return []

    def _schedule_custom_course_review(self, course_id, name):
        from .settings_feature import _course, _workers, _running
        course = _course(course_id)
        if not course or not course["active"] or course_id in _running:
            return False
        _workers.submit(__import__("my_ai.settings_feature", fromlist=["_run_course"])._run_course, course_id)
        next_review = (datetime.now(timezone.utc) + timedelta(days=REVIEW_DAYS)).isoformat()
        execute("UPDATE learning_domains SET last_review_at=CURRENT_TIMESTAMP,next_review_at=? WHERE name=?", (next_review, f"custom_course:{course_id}"))
        return True

    def _review_loop(self):
        while not self._review_stop.is_set():
            try:
                for name in due_domains():
                    if str(name).startswith("custom_course:"):
                        continue
                    if self._review_stop.is_set():
                        break
                    if not ensure_domain(name):
                        continue
                    try:
                        domain_rows = fetch_all("SELECT auto_learn FROM learning_domains WHERE name=?", (name,))
                        if domain_rows and int(domain_rows[0]["auto_learn"] or 0) != 1:
                            continue
                    except Exception:
                        pass
                    self.update_progress("weekly_review", name)
                    engine = LearningEngine()
                    result = weekly_review(name, engine.web, engine.llm)
                    new_source_topics = self._queue_new_source_learning(name)
                    if result.get("added") or new_source_topics:
                        self.last_result = {"status": "weekly_review", "language": name, **result, "new_source_topics": new_source_topics}
                        self.start(name)
                    self.update_progress("idle")
                for course_id, course_name in self._custom_course_due():
                    if self._review_stop.is_set():
                        break
                    try:
                        from .settings_feature import _review_custom_course
                        engine = LearningEngine()
                        review = _review_custom_course(course_id, engine.web, engine.llm)
                    except Exception as exc:
                        review = {"status": "error", "added": [], "updated": [], "error": str(exc)}
                        logger.exception("CUSTOM_COURSE_WEEKLY_REVIEW_FAILURE: course_id=%s", course_id)
                    if self._schedule_custom_course_review(course_id, course_name):
                        self.last_result = {
                            "status": "weekly_review",
                            "course": course_name,
                            "course_id": course_id,
                            "added_topics": review.get("added", []),
                            "updated_topics": review.get("updated", []),
                            "review_error": review.get("error"),
                        }
            except Exception as exc:
                self.error = str(exc)
            self._review_stop.wait(min(self.interval_seconds, 3600))

    def _schedule_worker_recovery(self, language, stop_event):
        if stop_event.is_set():
            return
        def recover():
            if stop_event.is_set():
                return
            try:
                rows = fetch_all("SELECT session_id,status FROM learning_workers WHERE language=? LIMIT 1", (language,))
                if rows and rows[0]["status"] in {"stopping", "completed"}:
                    return
                session_id = rows[0]["session_id"] if rows else None
                logger.warning("LEARNING_WORKER_RECOVER: language=%s session_id=%s reason=unexpected_worker_exit", language, session_id)
                self.start(language, session_id)
            except Exception:
                logger.exception("LEARNING_WORKER_RECOVERY_FAILURE: language=%s", language)
        threading.Timer(2.0, recover).start()

    def _loop(self, language, stop_event):
        engine = LearningEngine()
        consecutive_errors = 0
        slot_acquired = False
        try:
            while not stop_event.is_set():
                if not slot_acquired:
                    slot_acquired = self._worker_slots.acquire(timeout=0.5)
                    if not slot_acquired:
                        if stop_event.is_set():
                            break
                        continue
                try:
                    if language not in LANGUAGE_CURRICULA:
                        language = ensure_domain(language, getattr(engine, "llm", None)) or language
                    resources = self._wait_for_resources(stop_event)
                    self._update_worker(language, "starting", status="running")
                    logger.info("LEARNING_CYCLE_START: language=%s current_topic=%s", language, self.current_topic)
                    result = engine.learn_next(
                        language,
                        progress_callback=lambda stage, topic=None: self._update_worker(language, stage, topic),
                        stop_event=stop_event,
                    )
                    consecutive_errors = 0
                    self._update_worker(language, self.stage, result=result, status="running")
                    if result.get("status") == "completed":
                        topic = result.get("topic", {}).get("topic")
                        self._update_worker(language, "completed", topic=topic, result=result, status="running")
                        if self._domain_complete(language):
                            self._schedule_review(language)
                        continue
                    if result.get("status") == "complete":
                        self._update_worker(language, "completed", result=result, status="completed")
                        self._schedule_review(language)
                        stop_event.wait(60.0)
                        continue
                    if stop_event.wait(min(self.interval_seconds, 60)):
                        break
                except InterruptedError as exc:
                    reason = str(exc) or "stop_event/cancellation"
                    logger.warning(
                        "LEARNING_STOPPED: language=%s stage=%s topic=%s reason=%s",
                        language, self.stage, self.current_topic, reason,
                    )
                    self._update_worker(language, "idle", status="idle", error=reason)
                    break
                except Exception as exc:
                    if stop_event.is_set():
                        break
                    consecutive_errors += 1
                    logger.exception(
                        "LEARNING_FAILURE: language=%s stage=%s topic=%s consecutive_errors=%s error=%s",
                        language, self.stage, self.current_topic, consecutive_errors, exc,
                    )
                    result = {
                        "status": "error",
                        "error": str(exc),
                        "consecutive_errors": consecutive_errors,
                        "resources": resources if "resources" in locals() else resource_status(),
                    }
                    self._update_worker(language, "retrying", result=result, error=str(exc), status="retrying")
                    if stop_event.wait(min(60.0, 2.0 ** min(consecutive_errors, 5))):
                        break
        finally:
            logger.info(
                "LEARNING_WORKER_EXIT: language=%s stop_requested=%s stage=%s topic=%s error=%s",
                language, stop_event.is_set(), self.stage, self.current_topic, self.error,
            )
            if slot_acquired:
                try:
                    self._worker_slots.release()
                except ValueError:
                    pass
            unexpected_exit = not stop_event.is_set()
            with self._lock:
                self._workers.pop(language.casefold(), None)
                execute(
                    "UPDATE learning_workers SET status='idle',stage='idle',updated_at=CURRENT_TIMESTAMP WHERE language=? AND status='stopping'",
                    (language,),
                )
            if unexpected_exit:
                self._schedule_worker_recovery(language, stop_event)

