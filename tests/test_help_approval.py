from my_ai import api


def test_help_approve_applies_local_documentation(monkeypatch):
    calls=[]
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 1, "role": "admin"})
    monkeypatch.setattr(api, "fetch_all", lambda *args: [{"id": 5, "component": "chat", "proposed_update": "# Updated help"}])
    monkeypatch.setattr(api, "apply_help_update", lambda component, proposal: calls.append((component, proposal)) or True)
    monkeypatch.setattr(api, "execute", lambda *args: calls.append(args))
    result=api.help_approve(5, object())
    assert result["status"] == "approved"
    assert calls[0] == ("chat", "# Updated help")
