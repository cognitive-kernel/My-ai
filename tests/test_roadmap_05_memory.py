import inspect
from my_ai import memory


def test_memory_recall_is_available_with_metadata_support():
    assert hasattr(memory, "recall")
    params = inspect.signature(memory.recall).parameters
    assert "query" in params


def test_memory_module_exposes_store_and_delete_lifecycle():
    names = dir(memory)
    assert any(name in names for name in ("remember", "store", "add_memory"))
    assert any(name in names for name in ("delete_memory", "forget", "clear_memory"))
