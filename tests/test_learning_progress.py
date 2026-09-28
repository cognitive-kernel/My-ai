import sqlite3
import threading
import time

from my_ai import db as db_module
from my_ai import learner as learner_module
from my_ai.learner import LearningEngine
from my_ai.scheduler import StudyScheduler


def test_progress_deduplicates_topics_and_clamps_to_curriculum(monkeypatch):
    monkeypatch.setattr(
        learner_module,
        "LANGUAGE_CURRICULA",
        {
            "Python": [
                {"order": 1, "topic": "A", "goal": ""},
                {"order": 2, "topic": "B", "goal": ""},
            ],
            "SQL Server": [
                {"order": 1, "topic": "T-SQL", "goal": ""},
            ],
        },
    )
    monkeypatch.setattr(
        learner_module,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {"language": "Python", "topic": "A", "status": "completed", "score": 90},
            {"language": "Python", "topic": "A", "status": "completed", "score": 95},
            {"language": "Python", "topic": "B", "status": "completed", "score": 85},
            {"language": "Python", "topic": "not-in-curriculum", "status": "completed", "score": 100},
            {"language": "SQL Server", "topic": "T-SQL", "status": "completed", "score": 80},
        ],
    )

    result = LearningEngine.__new__(LearningEngine).status()
    python = next(x for x in result["languages"] if x["language"] == "Python")
    sql = next(x for x in result["languages"] if x["language"] == "SQL Server")

    assert python["completed_topics"] == 2
    assert python["total_topics"] == 2
    assert python["progress_percent"] == 100.0
    assert sql["progress_percent"] == 100.0
    assert python["progress_percent"] <= 100.0


def test_status_reconciles_completed_and_custom_persisted_tracks(monkeypatch):
    monkeypatch.setattr(
        learner_module,
        "LANGUAGE_CURRICULA",
        {
            "Python": [
                {"order": 1, "topic": "A", "goal": ""},
                {"order": 2, "topic": "B", "goal": ""},
            ],
            "Forex": [
                {"order": 1, "topic": "FX", "goal": ""},
            ],
        },
    )
    monkeypatch.setattr(
        learner_module,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {"language": "Python", "topic": "A", "status": "completed", "score": 90, "progress_percent": 100},
            {"language": "Python", "topic": "B", "status": "started", "score": None, "progress_percent": 25},
            {"language": "LegacyDynamicCourse", "topic": "LegacyDynamicCourse", "status": "started", "score": None, "progress_percent": 40},
            {"language": "Forex", "topic": "FX", "status": "completed", "score": 88, "progress_percent": 100},
        ],
    )
    result = LearningEngine.__new__(LearningEngine).status()
    summaries = {item["language"]: item for item in result["languages"]}

    assert summaries["Python"]["completed_topics"] == 1
    assert summaries["Python"]["remaining_topics"] == 1
    assert summaries["Python"]["progress_percent"] == 62.5
    assert summaries["LegacyDynamicCourse"]["remaining_topics"] == 1
    assert summaries["LegacyDynamicCourse"]["progress_percent"] == 40.0
    assert summaries["Forex"]["completed_topics"] == 1
    assert summaries["Forex"]["remaining_topics"] == 0
    assert summaries["Forex"]["progress_percent"] == 100.0
    assert "Forex" in result["available_languages"]

def test_half_percent_progress_grid_and_bounds():
    engine = LearningEngine.__new__(LearningEngine)
    assert engine._half_percent(0.49) == 0.5
    assert engine._half_percent(1.0) == 1.0
    assert engine._half_percent(1.24) == 1.0
    assert engine._half_percent(1.26) == 1.5
    assert engine._half_percent(100.0) == 100.0
    assert engine._half_percent(120.0) == 100.0


def test_scheduler_worker_uses_its_own_stop_event(monkeypatch):
    started = []
    release = threading.Event()

    class FakeEngine:
        def __init__(self):
            pass

        def learn_next(self, language, progress_callback=None, stop_event=None):
            started.append(language)
            release.wait(2)
            return {"status": "completed", "topic": {"topic": "test"}}

    monkeypatch.setattr("my_ai.scheduler.LearningEngine", FakeEngine)
    monkeypatch.setattr("my_ai.scheduler.StudyScheduler._wait_for_resources", staticmethod(lambda stop_event: {}))
    scheduler = StudyScheduler(interval_seconds=60)
    old_stop = threading.Event()
    old_thread = threading.Thread(target=scheduler._loop, args=("Python", old_stop), daemon=True)
    old_thread.start()
    time.sleep(0.05)
    old_stop.set()
    release.set()
    old_thread.join(timeout=1)
    assert not old_thread.is_alive()
    assert started == ["Python"]
    scheduler.stop()


def test_scheduler_runs_multiple_languages_concurrently(monkeypatch):
    started = []
    release = threading.Event()

    class FakeEngine:
        def __init__(self):
            pass

        def learn_next(self, language, progress_callback=None, stop_event=None):
            started.append(language)
            release.wait(1)
            return {"status": "completed", "topic": {"topic": "test"}}

    monkeypatch.setattr("my_ai.scheduler.LearningEngine", FakeEngine)
    monkeypatch.setattr("my_ai.scheduler.StudyScheduler._wait_for_resources", staticmethod(lambda stop_event: {}))
    scheduler = StudyScheduler(interval_seconds=60)
    scheduler.start("Python")
    scheduler.start("SQL Server")
    deadline = time.time() + 1
    while time.time() < deadline and set(started) != {"Python", "SQL Server"}:
        time.sleep(0.01)
    assert set(started) == {"Python", "SQL Server"}
    assert len(scheduler.status()["active_workers"]) == 2
    release.set()
    scheduler.stop()


def test_scheduler_status_returns_json_safe_snapshot():
    scheduler = StudyScheduler.__new__(StudyScheduler)
    scheduler.interval_seconds = 3600
    scheduler._thread = None
    scheduler.language = "SQL Server"
    scheduler.last_result = {"status": "completed", "score": 91}
    scheduler.current_topic = "T-SQL"
    scheduler.stage = "completed"
    scheduler.error = None
    scheduler._lock = threading.Lock()

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr("my_ai.scheduler.fetch_all", lambda *_args, **_kwargs: [])
    try:
        result = scheduler.status()
    finally:
        monkeypatch.undo()

    assert result["running"] is False
    assert result["language"] == "SQL Server"
    assert result["stage"] == "completed"
    assert result["current_topic"] == "T-SQL"
    assert result["last_result"] == {"status": "completed", "score": 91}
    assert result["error"] is None
    assert result["interval_seconds"] == 3600
    assert result["session_id"] is None
    assert result["runtime_status"] == "idle"
    assert result["runtime_updated_at"] is None
    assert result["workers"] == []
    assert result["active_workers"] == []
    assert "resources" in result


def test_knowledge_memory_deduplicates_normalized_content(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE knowledge (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, source_url TEXT, content_hash TEXT)"
    )
    monkeypatch.setattr(db_module, "connect", lambda: conn)

    first = db_module.remember_knowledge("Python", "One", "  Same   knowledge\ncontent. ")
    second = db_module.remember_knowledge("Python", "Two", "Same knowledge content.", "https://example.test/source")

    assert first == second
    rows = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    assert rows == 1
    source = conn.execute("SELECT source_url FROM knowledge WHERE id=?", (first,)).fetchone()[0]
    assert source == "https://example.test/source"
    conn.close()


def test_status_includes_active_topic_progress():
    original = learner_module.LANGUAGE_CURRICULA
    try:
        learner_module.LANGUAGE_CURRICULA = {
            "Python": [
                {"order": 1, "topic": "A", "goal": ""},
                {"order": 2, "topic": "B", "goal": ""},
            ]
        }
        learner_module.fetch_all = lambda *_args, **_kwargs: [
            {"language": "Python", "topic": "A", "status": "completed", "score": 80, "progress_percent": 100},
            {"language": "Python", "topic": "B", "status": "started", "score": None, "progress_percent": 25},
        ]
        result = LearningEngine.__new__(LearningEngine).status()
        python = result["languages"][0]
        assert python["progress_percent"] == 62.5
        assert python["average_score"] == 80.0
    finally:
        learner_module.LANGUAGE_CURRICULA = original


def test_assess_is_deterministic_and_returns_none_for_empty_lesson():
    engine = LearningEngine.__new__(LearningEngine)
    lesson = "Prerequisite Example Exercise Test Common mistakes Security Mastery checklist\\n" + ("x " * 3000)
    score = engine.assess("Python", lesson)
    assert score is not None
    assert 0.0 <= score <= 100.0
    assert engine.assess("Python", "") is None


def test_learning_retry_backoff_is_bounded(monkeypatch):
    attempts = []
    sleeps = []
    engine = LearningEngine.__new__(LearningEngine)
    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("temporary failure")
        return "ok"
    monkeypatch.setattr(learner_module.time, "sleep", lambda delay: sleeps.append(delay))
    assert engine._retry_with_limit(operation, "test", max_attempts=3) == "ok"
    assert len(attempts) == 3
    assert sleeps == [1.0, 2.0]


def test_learning_retry_can_be_explicitly_stopped():
    stop_event = threading.Event()
    calls = []

    def operation():
        calls.append(1)
        stop_event.set()
        raise RuntimeError("temporary failure")

    engine = LearningEngine.__new__(LearningEngine)
    try:
        engine._retry_with_limit(operation, "test", stop_event=stop_event)
    except InterruptedError:
        pass
    else:
        raise AssertionError("retry loop must stop when explicitly requested")

    assert calls == [1]


def test_learning_engine_keeps_compatible_retry_method():
    engine = LearningEngine.__new__(LearningEngine)
    assert hasattr(engine, "_retry_forever")


def test_detailed_status_exposes_every_curriculum_topic(monkeypatch):
    monkeypatch.setattr(learner_module, "fetch_all", lambda *_args, **_kwargs: [])
    engine = LearningEngine.__new__(LearningEngine)
    result = engine.detailed_status("Python")
    course = result["courses"][0]
    assert course["language"] == "Python"
    assert course["total_topics"] == len(learner_module.LANGUAGE_CURRICULA["Python"])
    assert course["completed_topics"] == 0
    assert course["remaining_topics"] == course["total_topics"]
    assert len(course["topics"]) == course["total_topics"]
    assert all(topic["progress_percent"] == 0 for topic in course["topics"])


def test_detailed_status_includes_complete_catalog_and_persisted_topics(monkeypatch):
    monkeypatch.setattr(
        learner_module,
        "LANGUAGE_CURRICULA",
        {
            "Python": [
                {"order": 1, "topic": "A", "goal": ""},
            ],
        },
    )
    monkeypatch.setattr(
        learner_module,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {"language": "Python", "topic": "A", "status": "completed", "score": 90, "progress_percent": 100, "phase": "completed", "created_at": "1"},
            {"language": "Python", "topic": "Docker", "status": "started", "score": None, "progress_percent": 25, "phase": "lesson", "created_at": "2"},
            {"language": "LegacyDynamicCourse", "topic": "LegacyDynamicCourse", "status": "started", "score": None, "progress_percent": 50, "phase": "sources", "created_at": "3"},
            {"language": "LegacyDynamicCourse", "topic": "Finished LegacyDynamicCourse", "status": "completed", "score": 95, "progress_percent": 100, "phase": "completed", "created_at": "4"},
        ],
    )
    engine = LearningEngine.__new__(LearningEngine)

    result = engine.detailed_status()
    courses = {item["language"]: item for item in result["courses"]}

    assert "Python" in courses
    assert [item["topic"] for item in courses["Python"]["topics"]] == ["A", "Docker"]
    assert courses["Python"]["topics"][0]["progress_percent"] == 100.0
    assert courses["Python"]["progress_percent"] == 62.5
    assert "LegacyDynamicCourse" in courses
    assert [item["topic"] for item in courses["LegacyDynamicCourse"]["topics"]] == ["LegacyDynamicCourse", "Finished LegacyDynamicCourse"]
    assert courses["LegacyDynamicCourse"]["topics"][1]["progress_percent"] == 100.0

def test_detailed_status_canonicalizes_persisted_language(monkeypatch):
    monkeypatch.setattr(
        learner_module,
        "LANGUAGE_CURRICULA",
        {"Forex": [{"order": 1, "topic": "FX", "goal": ""}]},
    )
    monkeypatch.setattr(
        learner_module,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {"language": "forex", "topic": "FX", "status": "completed", "score": 90, "progress_percent": 100, "phase": "completed", "created_at": "1"},
        ],
    )
    result = LearningEngine.__new__(LearningEngine).detailed_status()
    courses = {item["language"]: item for item in result["courses"]}
    assert courses["Forex"]["progress_percent"] == 100.0
    assert courses["Forex"]["topics"][0]["progress_percent"] == 100.0


def test_learning_source_failure_is_recorded_and_does_not_abort(monkeypatch):
    from my_ai.learner import LearningEngine

    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = type("LLM", (), {
        "chat": lambda self, prompt, system=None: "extracted note"
    })()
    engine.web = type("Web", (), {
        "fetch": lambda self, url, stop_event=None: (_ for _ in ()).throw(RuntimeError("connection failed"))
    })()

    monkeypatch.setattr("my_ai.learner.topic_source_urls", lambda _language, _topic: [
        "https://docs.example.test/tutorial/",
        "https://docs.example.test/library/",
    ])
    monkeypatch.setattr("my_ai.learner.seed_for", lambda *_args: "seed")
    monkeypatch.setattr("my_ai.learner.remember", lambda *args, **kwargs: None)
    monkeypatch.setattr("my_ai.learner.settings", type("Settings", (), {"learning_max_retries": 1, "learning_source_max_chars": 1000})())

    result = engine._learn_sources_for_topic(
        "Python",
        {"topic": "Import system", "goal": "imports"},
        [],
    )

    assert len(result) == 3
    assert all(item["title"] == "Source unavailable" for item in result[1:])
    assert all("connection failed" in item["error"] for item in result[1:])


def test_scheduler_logs_full_worker_exception(monkeypatch, caplog):
    import logging

    class FakeEngine:
        def __init__(self):
            pass
        def learn_next(self, language, progress_callback=None, stop_event=None):
            raise RuntimeError("source fetch exploded")

    monkeypatch.setattr("my_ai.scheduler.LearningEngine", FakeEngine)
    monkeypatch.setattr("my_ai.scheduler.StudyScheduler._wait_for_resources", staticmethod(lambda stop_event: {}))
    scheduler = StudyScheduler(interval_seconds=1)
    class StopOnce:
        def __init__(self):
            self.stopped = False
        def is_set(self):
            return self.stopped
        def wait(self, _timeout):
            self.stopped = True
            return True
    stop = StopOnce()
    with caplog.at_level(logging.ERROR, logger="my_ai.scheduler"):
        scheduler._loop("Python", stop)
    assert "LEARNING_FAILURE" in caplog.text
    assert "source fetch exploded" in caplog.text


def test_status_does_not_return_large_lesson_notes(monkeypatch):
    monkeypatch.setattr(learner_module, "LANGUAGE_CURRICULA", {"Python": [{"order": 1, "topic": "A", "goal": ""}]})
    huge = "x" * 5_000_000
    monkeypatch.setattr(learner_module, "fetch_all", lambda *_args, **_kwargs: [{"id": 1, "language": "Python", "topic": "A", "status": "completed", "score": 90, "progress_percent": 100, "phase": "completed", "created_at": "now", "notes": huge}])
    result = LearningEngine.__new__(LearningEngine).status()
    assert "notes" not in result["sessions"][0]
    assert result["languages"][0]["progress_percent"] == 100.0


def test_assessment_is_local_and_does_not_call_llm():
    class FailingLLM:
        def chat(self, *_args, **_kwargs):
            raise AssertionError("assessment must not call the model")
    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = FailingLLM()
    lesson = """Prerequisite\nExample\nExercise\nTest\nCommon mistakes\nSecurity\nMastery checklist\n""" + ("x " * 3000)
    score = engine.assess("Python", lesson)
    assert score is not None
    assert 0.0 <= score <= 100.0


def test_scheduler_worker_slot_limit(monkeypatch):
    monkeypatch.setattr("my_ai.scheduler.settings", type("S", (), {
        "scheduler_interval_seconds": 60,
        "scheduler_max_cpu_percent": 70,
        "scheduler_max_ram_percent": 80,
        "learning_max_concurrent_workers": 1,
    })())
    scheduler = StudyScheduler(interval_seconds=60)
    assert scheduler._worker_slots.acquire(blocking=False)
    assert scheduler._worker_slots.acquire(blocking=False) is False
    scheduler._worker_slots.release()


def test_scheduler_supervisor_does_not_resume_paused_worker(monkeypatch):
    scheduler = StudyScheduler.__new__(StudyScheduler)
    scheduler._supervisor_stop = threading.Event()
    scheduler._lock = threading.RLock()
    scheduler._workers = {}
    calls = []
    scheduler.start = lambda language, session_id=None: calls.append((language, session_id))
    queries = []

    def fake_fetch_all(query, *_args, **_kwargs):
        queries.append(query)
        return []

    monkeypatch.setattr("my_ai.scheduler.fetch_all", fake_fetch_all)
    scheduler._supervisor_stop.wait = lambda _timeout: scheduler._supervisor_stop.set()
    scheduler._supervisor_loop()
    assert calls == []
    assert "status IN ('running','retrying')" in queries[0]
    assert "'paused'" not in queries[0]

def test_scheduler_recovers_unexpected_worker_exit(monkeypatch):
    scheduler = StudyScheduler.__new__(StudyScheduler)
    calls = []
    scheduler.start = lambda language, session_id=None: calls.append((language, session_id))
    monkeypatch.setattr("my_ai.scheduler.fetch_all", lambda *_args, **_kwargs: [{"session_id": 7, "status": "running"}])

    class ImmediateTimer:
        def __init__(self, _delay, callback):
            self.callback = callback
        def start(self):
            self.callback()

    monkeypatch.setattr("my_ai.scheduler.threading.Timer", ImmediateTimer)
    stop_event = threading.Event()
    scheduler._schedule_worker_recovery("Python", stop_event)
    assert calls == [("Python", 7)]


def test_detailed_status_exposes_persisted_lesson_without_key_error(monkeypatch):
    monkeypatch.setattr(
        learner_module,
        "LANGUAGE_CURRICULA",
        {"Python": [{"order": 1, "topic": "A", "goal": "learn A"}]},
    )
    monkeypatch.setattr(
        learner_module,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {
                "id": 1,
                "language": "Python",
                "topic": "A",
                "status": "completed",
                "score": 95,
                "progress_percent": 100,
                "phase": "completed",
                "notes": "Full persisted lesson",
                "created_at": "2026-01-01 00:00:00",
            }
        ],
    )
    result = LearningEngine.__new__(LearningEngine).detailed_status()
    topic = result["courses"][0]["topics"][0]
    assert topic["lesson"] == "Full persisted lesson"
    assert topic["progress_percent"] == 100.0


def test_scheduler_does_not_infer_worker_language_from_latest_chat():
    scheduler = StudyScheduler.__new__(StudyScheduler)
    scheduler._latest_learning_message = lambda: "Learn Android security engineering"
    assert scheduler._normalize_language("PHP") == "PHP"


def test_learning_retry_does_not_repeat_permanent_http_error():
    engine = LearningEngine.__new__(LearningEngine)
    attempts = []

    class PermanentHTTPError(RuntimeError):
        response = type("Response", (), {"status_code": 403})()

    def operation():
        attempts.append(1)
        raise PermanentHTTPError("Forbidden")

    try:
        engine._retry_with_limit(operation, "source", max_attempts=3)
    except RuntimeError as exc:
        assert "permanently unavailable (HTTP 403)" in str(exc)
    else:
        raise AssertionError("permanent HTTP errors must fail without retrying")

    assert attempts == [1]


def test_personal_learning_experience_is_persisted(tmp_path, monkeypatch):
    old = db_module.settings.db_path
    object.__setattr__(db_module.settings, "db_path", str(tmp_path / "experience.db"))
    db_module.init_db()
    from my_ai.learner import LearningEngine
    engine = LearningEngine.__new__(LearningEngine)
    engine.record_experience("Python", "Functions", "error", "practice", "تمرین شکست خورد", "NameError")
    rows = engine.personal_experiences("Python", "Functions", 10)
    assert rows
    assert rows[0]["kind"] == "error"
    assert "NameError" == rows[0]["error"]


def test_personal_experience_can_be_disabled(tmp_path, monkeypatch):
    old = db_module.settings.db_path
    object.__setattr__(db_module.settings, "db_path", str(tmp_path / "experience-disabled.db"))
    db_module.init_db()
    from my_ai.learner import LearningEngine
    from my_ai.settings_store import set_setting
    engine = LearningEngine.__new__(LearningEngine)
    set_setting("learning.personal_experience", "false")
    assert engine.record_experience("Python", "Functions", "lesson", "learn", "lesson") is None
    assert engine.personal_experiences("Python", "Functions", 10) == []
