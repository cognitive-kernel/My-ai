import pytest

from my_ai import memory


def test_memory_tier_policies_are_registered():
    from my_ai.settings_store import SETTING_REGISTRY
    assert {"memory.short_term_policy", "memory.long_term_policy", "memory.experiential_policy"} <= SETTING_REGISTRY.keys()


def test_long_term_memory_policy_denies_writes(monkeypatch):
    monkeypatch.setattr("my_ai.settings_store.get_setting", lambda key, default=None: "deny" if key == "memory.long_term_policy" else default)
    with pytest.raises(PermissionError):
        memory.remember("topic", "title", "content")


def test_short_term_policy_helper_denies_approval_without_authorization(monkeypatch):
    monkeypatch.setattr("my_ai.settings_store.get_setting", lambda key, default=None: "approval" if key == "memory.short_term_policy" else default)
    with pytest.raises(PermissionError):
        memory._memory_write_allowed("short_term")


def test_experiential_memory_policy_denies_writes(monkeypatch):
    from my_ai.learner import LearningEngine
    monkeypatch.setattr("my_ai.settings_store.get_bool", lambda *args, **kwargs: True)
    monkeypatch.setattr("my_ai.settings_store.get_setting", lambda key, default=None: "deny" if key == "memory.experiential_policy" else default)
    engine = object.__new__(LearningEngine)
    with pytest.raises(PermissionError):
        engine.record_experience("Python", "topic", "test", "action", "content")
