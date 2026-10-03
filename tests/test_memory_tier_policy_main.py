import pytest

from my_ai import memory


def test_memory_tier_policies_are_independent():
    policies = memory.memory_policies()
    assert set(policies) == {"short_term", "long_term", "experiential"}
    assert all("allow_write" in value for value in policies.values())


def test_long_term_policy_denies_write(monkeypatch):
    monkeypatch.setattr(memory, "_memory_policy", lambda kind: {"allow_write": False, "allow_recall": True})
    with pytest.raises(PermissionError):
        memory.remember("topic", "title", "content", memory_type="long_term")


def test_short_term_policy_denies_write(monkeypatch):
    monkeypatch.setattr(memory, "_memory_policy", lambda kind: {"allow_write": False, "allow_recall": True})
    with pytest.raises(PermissionError):
        memory.remember("topic", "title", "content", memory_type="short_term")


def test_experiential_policy_denies_write(monkeypatch):
    monkeypatch.setattr(memory, "_memory_policy", lambda kind: {"allow_write": False, "allow_recall": True})
    with pytest.raises(PermissionError):
        memory.remember("topic", "title", "content", memory_type="experiential")
