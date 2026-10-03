from pathlib import Path


def test_legacy_router_is_only_a_facade():
    source = Path('my_ai/domain_router.py').read_text(encoding='utf-8')
    assert '_is_continuation' not in source
    assert '_is_actionable' not in source
    assert 'db_markers' not in source
    assert 'from .domain.router import' in source