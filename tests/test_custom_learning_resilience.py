def test_custom_learning_resilience_installs(monkeypatch):
    import my_ai.settings_feature as sf
    from my_ai.custom_learning_resilience import install

    monkeypatch.setattr(sf, "_myai_resilience_installed", False, raising=False)
    original = sf._run_course
    install()
    assert sf._run_course is not original
    assert sf._myai_resilience_installed is True
