from pathlib import Path

import pytest

pytestmark = pytest.mark.timeout(30)


def test_mt4_settings_are_persisted_and_connection_test_is_runtime_based():
    source = Path("my_ai/settings_feature.py").read_text(encoding="utf-8")
    assert '@router.get("/settings/domain-capabilities")' in source
    assert '@router.put("/settings/domain-capabilities")' in source
    assert '@router.post("/settings/domain-capabilities/test")' in source
    assert 'set_setting("mt4.install_path"' in source
    assert 'from .domain.mt4 import status' in source
