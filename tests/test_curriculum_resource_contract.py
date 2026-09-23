from my_ai.curriculum import LANGUAGE_CURRICULA


def test_python_curriculum_has_exactly_40_topics():
    topics = LANGUAGE_CURRICULA["Python"]
    assert len(topics) == 40
    assert len({str(item["topic"]) for item in topics}) == 40


def test_each_curriculum_count_matches_unique_topic_count():
    for language, topics in LANGUAGE_CURRICULA.items():
        assert len(topics) == len({str(item["topic"]) for item in topics}), language


def test_resource_settings_have_expected_defaults_and_ranges():
    from my_ai.settings_store import get_int, get_setting

    assert float(get_setting("resources.cpu_percent", "70")) == 70.0
    assert get_int("resources.cpu_threads", 8) == 8
    assert float(get_setting("resources.ram_percent", "80")) == 80.0
    assert get_int("resources.gpu_layers", 0) == 0


def test_forex_curriculum_is_a_complete_learning_package():
    topics = LANGUAGE_CURRICULA["Forex"]
    assert len(topics) == 120
    assert len({str(item["topic"]) for item in topics}) == 120
    assert topics[0]["topic"] == "Forex fundamentals"
    assert topics[-1]["topic"] == "Forex and MetaTrader expert capstone"
    assert any("MQL4" in str(item["topic"]) for item in topics)
    assert any("MQL5" in str(item["topic"]) for item in topics)
    assert any("Ichimoku" in str(item["topic"]) for item in topics)
    assert any("Bollinger Bands" in str(item["topic"]) for item in topics)
