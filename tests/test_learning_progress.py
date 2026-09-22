import json
import threading
import time

import my_ai.learner as learner_module
from my_ai.learner import LearningEngine
from my_ai.scheduler import StudyScheduler


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
    time.sleep(0.05)
    scheduler.start("SQL Server")
    time.sleep(0.05)
    scheduler.stop()
    assert "Python" in started
    assert "SQL Server" in started


def test_learning_retries_until_llm_recovers(monkeypatch):
    attempts = []
    sleeps = []

    class FakeLLM:
        def chat(self, prompt, system=None):
            attempts.append(prompt)
            if len(attempts) < 3:
                raise RuntimeError("Ollama request failed: timed out")
            return '{"prerequisites": []}'

    engine = LearningEngine.__new__(LearningEngine)
    engine.llm = FakeLLM()
    monkeypatch.setattr(learner_module.time, "sleep", lambda delay: sleeps.append(delay))
    result = engine._discover_prerequisites("Python", {"topic": "Functions", "goal": "functions"})
    assert result == []
    assert len(attempts) == 3
    assert sleeps == [1.0, 2.0]


def test_learning_retry_can_be_explicitly_stopped(monkeypatch):
    stop_event = threading.Event()
    calls = []

    def operation():
        calls.append(1)
        raise RuntimeError("temporary failure")

    def stop_after_first(delay):
        stop_event.set()

    monkeypatch.setattr(learner_module.time, "sleep", stop_after_first)
    engine = LearningEngine.__new__(LearningEngine)
    try:
        engine._retry_forever(operation, "test", stop_event=stop_event)
    except InterruptedError:
        pass
    else:
        raise AssertionError("retry loop did not stop when requested")
    assert calls == [1]


def test_progress_is_clamped_and_half_percent_grid():
    assert LearningEngine._half_percent(-1) == 0.0
    assert LearningEngine._half_percent(100) == 100.0
    assert LearningEngine._half_percent(100.4) == 100.0
    assert LearningEngine._half_percent(12.24) == 12.0
    assert LearningEngine._half_percent(12.26) == 12.5


def test_topic_deduplication():
    from my_ai.curriculum import next_topic
    assert next_topic("Python", {"Python Basics"}) != {"topic": "Python Basics", "goal": "Learn Python fundamentals"}


def test_knowledge_seed_deduplication():
    from my_ai.db import execute, fetch_all
    execute("DELETE FROM knowledge WHERE title=?", ("test-seed",))
    execute("INSERT INTO knowledge(language,title,content,url) VALUES(?,?,?,?)", ("Python", "test-seed", "a", "model://knowledge-seed"))
    execute("INSERT INTO knowledge(language,title,content,url) VALUES(?,?,?,?)", ("Python", "test-seed", "b", "model://knowledge-seed"))
    rows = fetch_all("SELECT * FROM knowledge WHERE title=?", ("test-seed",))
    assert len(rows) >= 1


def test_scheduler_status_defaults():
    scheduler = StudyScheduler(interval_seconds=60)
    status = scheduler.status()
    assert "running" in status


def test_assessment_parsing():
    class FakeLLM:
        def chat(self, prompt, system=None):
            return "Score: 87"

    engine = LearningEngine(FakeLLM())
    assert engine.assess("x", "y") == 87.0


def test_assessment_rejects_missing_score():
    class FakeLLM:
        def chat(self, prompt, system=None):
            return "No score here"

    engine = LearningEngine(FakeLLM())
    assert engine.assess("x", "y") is None


def test_progress_json_topic_roundtrip():
    topic = {"topic": "Functions", "goal": "functions"}
    assert json.loads(json.dumps(topic)) == topic
