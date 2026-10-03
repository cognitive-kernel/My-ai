from my_ai import settings_feature


def test_prompt_test_uses_registered_prompt_task(monkeypatch):
    monkeypatch.setattr(settings_feature, "require_admin", lambda request: {"id": 1})
    monkeypatch.setattr(
        settings_feature,
        "get_record",
        lambda namespace, name: {"name": name, "payload": {"text": "You are concise.", "task": "coding"}},
    )

    class FakeLLM:
        def chat(self, message, system=None):
            assert message == "hello"
            assert system == "You are concise."
            return "tested"

    monkeypatch.setattr(settings_feature, "create_llm", lambda task: (assert_task(task), FakeLLM())[1])
    monkeypatch.setattr(settings_feature, "audit", lambda *args: None)
    result = settings_feature.settings_prompt_test(
        "demo",
        settings_feature.PromptTestRequest(input="hello"),
        object(),
    )
    assert result["output"] == "tested"


def assert_task(task):
    assert task == "coding"


def test_prompt_test_rejects_missing_prompt(monkeypatch):
    monkeypatch.setattr(settings_feature, "require_admin", lambda request: {"id": 1})
    monkeypatch.setattr(settings_feature, "get_record", lambda namespace, name: None)
    try:
        settings_feature.settings_prompt_test(
            "missing",
            settings_feature.PromptTestRequest(input="hello"),
            object(),
        )
    except settings_feature.HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("missing prompt must be rejected")
