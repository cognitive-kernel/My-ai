    monkeypatch.setattr(learner_module.time, "sleep", lambda delay: sleeps.append(delay))

    result = engine._discover_prerequisites(
        "Python",
        {"topic": "Functions", "goal": "functions"},
    )

    assert result == []
    assert len(attempts) == 3
    assert sleeps == [0.1, 1.0, 2.0]


def test_learning_retry_can_be_explicitly_stopped():
    stop_event = threading.Event()