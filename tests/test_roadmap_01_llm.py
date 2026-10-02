from my_ai import provider_catalog


def test_provider_key_rotation_and_activation_contract(monkeypatch):
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params=()):
            class Cur:
                def fetchall(self):
                    return [
                        {"id": 1, "key_name": "primary", "active": 1, "priority": 10},
                        {"id": 2, "key_name": "backup", "active": 0, "priority": 20},
                    ]
                def fetchone(self): return {"id": 2, "key_name": "backup"}
            return Cur()
        def commit(self): pass

    monkeypatch.setattr(provider_catalog, "connect", lambda: FakeConn())
    monkeypatch.setattr(provider_catalog, "ensure_schema", lambda: None)
    monkeypatch.setattr(provider_catalog, "assert_mutation_allowed", lambda *_: None)
    rotated = provider_catalog.rotate_provider_key(1)
    assert rotated["active_key"] == "backup"
    assert rotated["previous_key"] == "primary"


def test_runtime_provider_config_exposes_auth_metadata():
    import inspect
    assert hasattr(provider_catalog, "get_provider_runtime_config")
    assert "provider_id" in inspect.signature(provider_catalog.get_provider_runtime_config).parameters
