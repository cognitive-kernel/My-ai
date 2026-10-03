from types import SimpleNamespace

import my_ai.capability_runtime as runtime


def test_metatrader_capability_is_not_run_for_chat(monkeypatch):
    called = []
    monkeypatch.setattr(runtime, "_metatrader", lambda message: called.append(message))
    intent = SimpleNamespace(name="chat", intents=("chat",))
    assert runtime.run(intent, "سلام") is None
    assert called == []


def test_metatrader_capability_runs_only_when_semantically_routed(monkeypatch):
    expected = runtime.CapabilityResult(
        name="metatrader.connection",
        available=True,
        evidence="LIVE METATRADER CONNECTION",
    )
    monkeypatch.setattr(runtime, "_metatrader", lambda message: expected)
    monkeypatch.setattr(runtime, "get", lambda name: SimpleNamespace(verifier=runtime._verify_result))
    intent = SimpleNamespace(name="metatrader", intents=("metatrader",))
    result = runtime.run(intent, "با تنظیمات ذخیره‌شده به Forex وصل شو")
    assert result == expected
