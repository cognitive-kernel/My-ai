from my_ai.curriculum import PYTHON_CURRICULUM, SQLSERVER_CURRICULUM, LANGUAGE_CURRICULA, next_topic
from my_ai.topic_resources import validate_topic_resources, supplementary_source_urls
from my_ai.learner import LearningEngine


def test_curriculum_has_core_topics():
    topics = {str(item["topic"]) for item in PYTHON_CURRICULUM}
    assert "Functions" in topics
    assert "Testing" in topics
    assert "HTTP and APIs" in topics


def test_advanced_curriculum_is_present():
    python_topics = {str(item["topic"]) for item in LANGUAGE_CURRICULA["Python"]}
    sql_topics = {str(item["topic"]) for item in LANGUAGE_CURRICULA["SQL Server"]}
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


def test_every_curriculum_topic_has_supplementary_resources():
    missing = validate_topic_resources(LANGUAGE_CURRICULA)
    assert missing == []
    for language, topics in LANGUAGE_CURRICULA.items():
        for item in topics:
            assert len(supplementary_source_urls(language, item["topic"])) >= 2


def test_forex_curriculum_is_fully_covered():
    forex_topics = LANGUAGE_CURRICULA["Forex"]
    assert len(forex_topics) >= 120
    assert not validate_topic_resources({"Forex": forex_topics})


def test_cisco_curriculum_is_available_from_zero():
    from my_ai.curriculum import LANGUAGE_ALIASES, LANGUAGE_SOURCES
    topics = LANGUAGE_CURRICULA["Cisco"]
    assert len(topics) >= 40
    assert topics[0]["topic"] == "Networking fundamentals"
    assert topics[-1]["topic"] == "Cisco networking capstone"
    assert LANGUAGE_ALIASES["cisco"] == "Cisco"
    assert LANGUAGE_ALIASES["سیسکو"] == "Cisco"
    assert any("cisco.com" in url for url in LANGUAGE_SOURCES["Cisco"])
