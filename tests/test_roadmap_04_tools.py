from my_ai import registries


def test_tool_registry_publishes_full_runtime_contract(monkeypatch):
    captured = {}
    monkeypatch.setattr(registries, "put_record", lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {"ok": True})
    result = registries.register_tool(
        "demo", "Demo tool", {"type": "object"}, {"type": "object"},
        permissions=["read"], timeout=12, retries=3, tasks=["chat"], version="2", enabled=True
    )
    assert result["ok"] is True
    payload = captured["args"][2]
    assert payload["description"] == "Demo tool"
    assert payload["input_schema"]["type"] == "object"
    assert payload["permissions"] == ["read"]
    assert payload["timeout"] == 12
    assert payload["retries"] == 3
    assert payload["version"] == "2"
    assert captured["kwargs"]["enabled"] is True


def test_prompt_registry_is_versioned(monkeypatch):
    captured = {}
    monkeypatch.setattr(registries, "put_record", lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {})
    registries.publish_prompt("p", "hello", task="chat", version="3")
    assert captured["args"][2]["version"] == "3"


def test_tool_registry_edit_preserves_identity(monkeypatch):
    records = {"demo": {"name": "demo", "payload": {}}}
    monkeypatch.setattr(registries, "get_record", lambda namespace, name: records.get(name))
    monkeypatch.setattr(registries, "put_record", lambda *args, **kwargs: {"name": args[1], "payload": args[2], "enabled": kwargs["enabled"]})
    result = registries.update_tool("demo", "edited", {"type":"object"}, {"type":"string"}, timeout=12, retries=4, version="2")
    assert result["name"] == "demo"
    assert result["payload"]["description"] == "edited"
    assert result["payload"]["version"] == "2"


def test_workflow_registry_edit_preserves_identity(monkeypatch):
    import my_ai.registries as registries
    records={"demo":{"name":"demo","payload":{}}}
    monkeypatch.setattr(registries,"get_record",lambda namespace,name: records.get(name))
    monkeypatch.setattr(registries,"put_record",lambda *args,**kwargs: {"name":args[1],"payload":args[2],"enabled":kwargs["enabled"]})
    result=registries.update_workflow("demo",[{"name":"stage1","enabled":True}],version="2")
    assert result["name"]=="demo"
    assert result["payload"]["version"]=="2"


def test_tool_health_reports_language_toolchains(monkeypatch):
    import my_ai.tooling as tooling
    monkeypatch.setattr(tooling, "doctor", lambda language=None: {language: {"python": True}})
    result = tooling.tool_health()
    assert result["healthy"] is True
    assert result["languages"]["Python"]["healthy"] is True
