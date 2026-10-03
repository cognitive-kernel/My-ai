from my_ai.control_plane import get_record, put_record
from my_ai import memory


def test_separate_memory_policies_are_seeded():
    policies = memory.memory_policies()
    assert set(policies) == {"short_term", "long_term", "experiential"}
    assert policies["short_term"]["retention_days"] == 7
    assert policies["long_term"]["retention_days"] == 365
    assert policies["experiential"]["retention_days"] == 3650


def test_memory_write_obeys_selected_policy(monkeypatch):
    put_record("memory.policy", "short_term", {"allow_write": False, "allow_recall": True, "retention_days": 1, "scope": "session"})
    try:
        try:
            memory.remember("t", "title", "content", memory_type="short_term")
            assert False, "write should be denied"
        except PermissionError:
            pass
    finally:
        put_record("memory.policy", "short_term", {"allow_write": True, "allow_recall": True, "retention_days": 7, "scope": "session"})


def test_memory_policy_is_independently_editable():
    put_record("memory.policy", "experiential", {"allow_write": True, "allow_recall": False, "retention_days": 90, "scope": "experience"})
    try:
        assert get_record("memory.policy", "experiential")["payload"]["allow_recall"] is False
        assert memory.recall("anything", memory_type="experiential") == []
    finally:
        put_record("memory.policy", "experiential", {"allow_write": True, "allow_recall": True, "retention_days": 3650, "scope": "experience"})
