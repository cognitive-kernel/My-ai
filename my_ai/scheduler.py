from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

from .learner import LearningEngine
from .platform import resource_status
from .curriculum import LANGUAGE_CURRICULA, LANGUAGE_SOURCES, canonical_language
from .db import execute, fetch_all
from .domain_registry import load_saved_domains
from .dynamic_learning import REVIEW_DAYS, ensure_domain, resolve_learning_target, due_domains, weekly_review


class StudyScheduler:
    def __init__(self, interval_seconds=3600):
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._review_stop = threading.Event()
        self._thread = None
        self._monitor_thread = None
        self.language = "Python"
        self.last_result = None
        self.current_topic = None
        self.stage = "idle"
        self.error = None
        self._lock = threading.Lock()
        try:
            load_saved_domains()
        except Exception as exc:
            self.error = str(exc)
        self._monitor_thread = None

    def start_review_monitor(self):
        if self._monitor_thread and self._monitor_thread.is_alive(): return
        self._review_stop.clear()
        self._monitor_thread = threading.Thread(target=self._review_loop, daemon=True, name="myai-weekly-review")
        self._monitor_thread.start()

    def start(self, language="Python"):
        language = str(language or "Python").strip() or "Python"
        known = canonical_language(language)
        if known in LANGUAGE_CURRICULA:
            language = known
        else:
            language = resolve_learning_target(self._latest_learning_message(), language)
            language = ensure_domain(language, LearningEngine().llm) or canonical_language(language)

        if self._thread and self._thread.is_alive():
            if self.language == language:
                return
            old_stop = self._stop
            old_stop.set()
            self._thread.join(timeout=5.0)

        self.language = language
        self.last_result = None
        self.error = None
        self.stage = "starting"
        self.current_topic = None
        worker_stop = threading.Event()
        self._stop = worker_stop
        self._thread = threading.Thread(
            target=self._loop,
            args=(language, worker_stop),
            daemon=True,
            name=f"myai-learning-{language}",
        )
        self._thread.start()

    def stop_learning(self):
        self._stop.set()
        self.stage = "stopping"

    def stop(self):
        self.stop_learning()
        self.stop_review_monitor()

    def stop_review_monitor(self):
        self._review_stop.set()

    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def status(self):
        """Return a JSON-safe snapshot for the API/UI scheduler dashboard."""
        with self._lock:
            last_result = self.last_result
            return {
                "running": self.running(),
                "language": self.language,
                "stage": self.stage,
                "current_topic": self.current_topic,
                "last_result": last_result,
                "error": self.error,
                "interval_seconds": self.interval_seconds,
            }

    def update_progress(self, stage, topic=None):
        with self._lock:
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
                last_review_at TEXT, next_review_at TEXT
            )"""
        )
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

    def _review_loop(self):
        while not self._review_stop.is_set():
            try:
                for name in due_domains():
                    if self._review_stop.is_set():
                        break
                    if not ensure_domain(name):
                        continue
                    if not self._domain_complete(name):
                        continue
                    self.update_progress("weekly_review", name)
                    engine = LearningEngine()
                    result = weekly_review(name, engine.web, engine.llm)
                    if result.get("added"):
                        self.last_result = {"status": "weekly_review", "language": name, **result}
                    self.update_progress("idle")
            except Exception as exc:
                self.error = str(exc)
            self._review_stop.wait(min(self.interval_seconds, 3600))

    def _loop(self, language, stop_event=None):
        # Bind the worker to its own immutable stop event. Replacing self._stop
        # for a new language must never revive or redirect an older worker.
        stop_event = stop_event or self._stop
        engine = LearningEngine()
        while not stop_event.is_set():
            try:
                if language not in LANGUAGE_CURRICULA:
                    language = ensure_domain(language, getattr(engine, "llm", None)) or language
                    self.language = language
                limits_cpu = float(__import__("os").getenv("SCHEDULER_MAX_CPU_PERCENT", "90"))
                limits_ram = float(__import__("os").getenv("SCHEDULER_MAX_RAM_PERCENT", "90"))
                resources = resource_status()
                if resources.get("cpu_percent") is not None and (resources["cpu_percent"] > limits_cpu or resources["ram_percent"] > limits_ram):
                    self.update_progress("paused", "system load high")
                    self.last_result = {"status":"paused","reason":"system load high","resources":resources}
                    stop_event.wait(min(self.interval_seconds, 60))
                    continue
                self.update_progress("starting")
                self.last_result = engine.learn_next(language, progress_callback=self.update_progress, stop_event=stop_event)
                if self.last_result.get("status") == "completed":
                    self.update_progress("completed", self.last_result.get("topic", {}).get("topic"))
                    if self._domain_complete(language):
                        self._schedule_review(language)
                elif self.last_result.get("status") == "complete":
                    self.update_progress("completed")
                    self._schedule_review(language)
                    break
            except InterruptedError:
                break
            except Exception as exc:
                if stop_event.is_set():
                    break
                self.error = str(exc)
                self.last_result = {"status": "error", "error": str(exc)}
                self.update_progress("retrying")
                # Unexpected errors outside the engine's retry boundary are also retried.
                stop_event.wait(1.0)
                continue
            if self.last_result and self.last_result.get("message", "").endswith("complete."):
                self._schedule_review(language)
                break
            if stop_event.wait(self.interval_seconds):
                break
