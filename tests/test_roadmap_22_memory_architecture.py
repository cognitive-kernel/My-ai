from my_ai.settings_store import SETTING_REGISTRY


def test_memory_architecture_controls_are_explicit():
    expected = {"memory.backend", "memory.retention_days", "memory.duplicate_threshold", "memory.chunk_size", "memory.chunk_overlap", "memory.embedding_model"}
    assert expected <= SETTING_REGISTRY.keys()
    assert SETTING_REGISTRY["memory.retention_days"]["min"] >= 1
    assert SETTING_REGISTRY["memory.duplicate_threshold"]["max"] == 1
