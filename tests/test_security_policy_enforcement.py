import pytest
from my_ai.control_plane import export_namespace

def test_export_policy_requires_approval(monkeypatch):
    monkeypatch.setattr("my_ai.control_plane.get_record", lambda namespace, name: {"enabled": True, "payload": {"allow": True, "require_approval": True}} if namespace == "security.export" else None)
    with pytest.raises(PermissionError):
        export_namespace("agent.budget")
    result = export_namespace("agent.budget", approved=True)
    assert result["namespace"] == "agent.budget"

def test_export_policy_can_deny(monkeypatch):
    monkeypatch.setattr("my_ai.control_plane.get_record", lambda namespace, name: {"enabled": True, "payload": {"allow": False, "require_approval": False}} if namespace == "security.export" else None)
    with pytest.raises(PermissionError):
        export_namespace("agent.budget", approved=True)
