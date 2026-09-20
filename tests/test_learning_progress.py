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

        def learn_next(self, language, progress_callback=None):
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

        def learn_next(self, language, progress_callback=None):
            started.append(language)
            return {"status": "completed", "topic": {"topic": "test"}}

    monkeypatch.setattr("my_ai.scheduler.LearningEngine", FakeEngine)
    scheduler = StudyScheduler(interval_seconds=60)
    scheduler.start("Python")
    scheduler.start("SQL Server")
    assert scheduler.language == "SQL Server"
    scheduler.stop()


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
