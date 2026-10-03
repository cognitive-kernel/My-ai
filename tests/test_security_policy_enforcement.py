import pytest
from my_ai.control_plane import export_namespace
from my_ai.security_catalog import set_export_policy

def test_export_policy_requires_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_AI_DB_PATH", str(tmp_path / "test.db"))
    set_export_policy("default", allow=True, require_approval=True)
    with pytest.raises(PermissionError):
        export_namespace("agent.budget")
    result = export_namespace("agent.budget", approved=True)
    assert result["namespace"] == "agent.budget"

def test_export_policy_can_deny(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_AI_DB_PATH", str(tmp_path / "test.db"))
    set_export_policy("default", allow=False, require_approval=False)
    with pytest.raises(PermissionError):
        export_namespace("agent.budget", approved=True)
