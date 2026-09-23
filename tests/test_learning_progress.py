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


def test_scheduler_switches_language_when_already_running(monkeypatch):
    started = []

    class FakeEngine:
        def __init__(self):
            pass

        def learn_next(self, language, progress_callback=None, stop_event=None):
            started.append(language)
            return {"status": "completed", "topic": {"topic": "test"}}

    monkeypatch.setattr("my_ai.scheduler.LearningEngine", FakeEngine)
    scheduler = StudyScheduler(interval_seconds=60)
    scheduler.start("Python")
    scheduler.start("SQL Server")
    assert scheduler.language == "SQL Server"
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

    result = scheduler.status()

    assert result == {
        "running": False,
        "language": "SQL Server",
        "stage": "completed",
        "current_topic": "T-SQL",
        "last_result": {"status": "completed", "score": 91},
        "error": None,
        "interval_seconds": 3600,
    }


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


def test_assess_parses_score_and_returns_none_for_invalid_output():
    class FakeLLM:
        def __init__(self, value):
            self.value = value
        def chat(self, *_args, **_kwargs):
            return self.value

    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = FakeLLM("Score: 82/100")
    assert engine.assess("Python", "lesson") == 82.0
    engine.llm = FakeLLM("unable to score")
    assert engine.assess("Python", "lesson") is None


def test_learning_retries_until_llm_recovers(monkeypatch):
    # Retry backoff starts at 1 second for the bounded retry path.
    attempts = []
    sleeps = []

    class FakeLLM:
        def chat(self, *_args, **_kwargs):
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise RuntimeError("Ollama request failed: timed out")
            return '{"prerequisites": []}'

    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = FakeLLM()
    monkeypatch.setattr(learner_module.time, "sleep", lambda delay: sleeps.append(delay))

    result = engine._discover_prerequisites(
        "Python",
        {"topic": "Functions", "goal": "functions"},
    )

    assert result == []
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


def test_learning_source_failure_is_recorded_and_does_not_abort(monkeypatch):
    from my_ai.learner import LearningEngine

    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = type("LLM", (), {
        "chat": lambda self, prompt, system=None: "extracted note"
    })()
    engine.web = type("Web", (), {
        "fetch": lambda self, url: (_ for _ in ()).throw(RuntimeError("connection failed"))
    })()

    monkeypatch.setattr("my_ai.learner.source_urls", lambda _language: [
        "https://docs.example.test/tutorial/",
        "https://docs.example.test/library/",
    ])
    monkeypatch.setattr("my_ai.learner.seed_for", lambda *_args: "seed")
    monkeypatch.setattr("my_ai.learner.remember", lambda *args, **kwargs: None)
    monkeypatch.setattr("my_ai.learner.settings", type("Settings", (), {"learning_max_retries": 1})())

    result = engine._learn_sources_for_topic(
        "Python",
        {"topic": "Import system", "goal": "imports"},
        [],
    )

    assert len(result) == 3
    assert all(item["title"] == "Source unavailable" for item in result[1:])
    assert all("connection failed" in item["error"] for item in result[1:])
