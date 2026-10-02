import httpx
from my_ai.infra import llm as llm_module

def test_openai_chat_has_bounded_retry_and_timeout(monkeypatch):
    class Settings:
        offline_strict=False
        openai_base_url="http://example.test"
        openai_model="model"
        openai_api_key="secret"
        llm_retry_attempts=2
        llm_retry_backoff_seconds=0
        llm_timeout_seconds=7
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    client=llm_module.OpenAICompatibleClient()
    calls=[]
    def post(*args, **kwargs):
        calls.append(kwargs["timeout"])
        if len(calls)==1:
            raise httpx.ReadTimeout("first")
        return type("R", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"output_text":"ok","usage":{}},
        })()
    monkeypatch.setattr(llm_module.httpx, "post", post)
    assert client.chat("hello")=="ok"
    assert calls==[7,7]
