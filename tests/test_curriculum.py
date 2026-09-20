from my_ai.curriculum import PYTHON_CURRICULUM, SQLSERVER_CURRICULUM, next_topic
from my_ai.learner import LearningEngine


def test_curriculum_has_core_topics():
    topics = {str(item["topic"]) for item in PYTHON_CURRICULUM}
    assert "Functions" in topics
    assert "Testing" in topics
    assert "HTTP and APIs" in topics


def test_advanced_curriculum_is_present():
    python_topics = {str(item["topic"]) for item in PYTHON_CURRICULUM}
    sql_topics = {str(item["topic"]) for item in SQLSERVER_CURRICULUM}
    assert "Descriptors" in python_topics
    assert "CPython and bytecode" in python_topics
    assert "Execution plans" in sql_topics
    assert "Deadlocks and concurrency diagnosis" in sql_topics


def test_next_topic_skips_completed():
    assert next_topic({"Syntax and execution"})["topic"] == "Variables and types"


def test_progress_uses_half_percent_steps():
    assert LearningEngine._half_percent(0.49) == 0.5
    assert LearningEngine._half_percent(1.24) == 1.0
    assert LearningEngine._half_percent(1.26) == 1.5
