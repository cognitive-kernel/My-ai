from my_ai.curriculum import LANGUAGE_CURRICULA
from my_ai.learner import LearningEngine


def test_python_curriculum_has_exactly_40_topics():
    python = LANGUAGE_CURRICULA["Python"]
    assert len(python) == 40
    assert max(int(item["order"]) for item in python) == 40
    assert len({str(item["topic"]) for item in python}) == 40


def test_sql_server_curriculum_uses_its_own_endpoint():
    sql = LANGUAGE_CURRICULA["SQL Server"]
    assert len(sql) == 30
    assert max(int(item["order"]) for item in sql) == 30


def test_status_counts_only_topics_belonging_to_selected_curriculum(monkeypatch):
    monkeypatch.setattr(
        "my_ai.learner.fetch_all",
        lambda *_args, **_kwargs: [
            {"language": "Python", "topic": "Syntax and execution", "status": "completed", "score": 90, "progress_percent": 100},
            {"language": "Python", "topic": "Advanced architecture and design", "status": "completed", "score": 100, "progress_percent": 100},
        ],
    )
    result = LearningEngine.__new__(LearningEngine).status("Python")
    python = result["languages"][0]
    assert python["total_topics"] == 40
    assert python["completed_topics"] == 1
    assert python["remaining_topics"] == 39
