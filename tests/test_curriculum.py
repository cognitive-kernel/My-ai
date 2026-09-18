from my_ai.curriculum import PYTHON_CURRICULUM, next_topic


def test_curriculum_has_core_topics():
    topics = {str(item["topic"]) for item in PYTHON_CURRICULUM}
    assert "Functions" in topics
    assert "Testing" in topics
    assert "HTTP and APIs" in topics


def test_next_topic_skips_completed():
    assert next_topic({"Syntax and execution"})["topic"] == "Variables and types"
