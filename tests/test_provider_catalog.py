import sqlite3

import my_ai.provider_catalog as catalog


def _connect_factory(path):
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    return connect


def test_provider_catalog_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "connect", _connect_factory(tmp_path / "catalog.db"))
    monkeypatch.setattr(catalog, "assert_mutation_allowed", lambda action: None)
    catalog.ensure_schema()
    provider = catalog.upsert_provider(name="custom", protocol="openai-compatible", endpoint="http://localhost:1234/v1", auth_type="bearer", secret="secret", capabilities={"chat": True, "streaming": True}, version="1")
    assert provider["name"] == "custom"
    assert provider["auth_configured"] is True
    model = catalog.upsert_model(provider_id=provider["id"], model_id="model-1", tasks=["chat"], context_length=8192, priority=10)
    assert model["model_id"] == "model-1"
    assert catalog.list_models(provider_id=provider["id"])[0]["context_length"] == 8192
    exported = catalog.export_catalog()
    assert exported["version"] == 2
    assert "auth_configured" not in exported["providers"][0]


def test_routing_and_fallback_catalog_persist(monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "connect", _connect_factory(tmp_path / "routing.db"))
    monkeypatch.setattr(catalog, "assert_mutation_allowed", lambda action: None)
    catalog.ensure_schema()
    provider = catalog.upsert_provider(name="route-provider", protocol="generic", endpoint="http://localhost:1234")
    catalog.upsert_model(provider_id=provider["id"], model_id="chat-a", tasks=["chat"], priority=10)
    catalog.upsert_model(provider_id=provider["id"], model_id="chat-b", tasks=["chat"], priority=20)
    rule = catalog.set_routing_rule("chat", "chat-b", provider_id=provider["id"], priority=1)
    assert rule["model_id"] == "chat-b"
    catalog.set_fallback_chain("ui", "chat", ["chat-b", "chat-a"])
    assert [x["model_id"] for x in catalog.list_fallback_chain("ui", "chat")] == ["chat-b", "chat-a"]
    assert catalog.list_routing_rules(task="chat")[0]["model_id"] == "chat-b"