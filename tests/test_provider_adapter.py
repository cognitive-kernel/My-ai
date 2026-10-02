from my_ai.infra.provider import (
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderHealth,
    ProviderRegistry,
    ProviderResponse,
    TokenUsage,
)


class DummyProvider:
    name = "dummy"
    capabilities = ProviderCapabilities(streaming=True, structured_output=True)

    def __init__(self, value="ok"):
        self.value = value

    def chat(self, message, *, system=None, history=None):
        return ProviderResponse(self.value, TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3))

    def stream_chat(self, message, *, system=None, history=None):
        yield self.value

    def structured_chat_json(self, message, schema, *, system=None):
        return {"ok": True}

    def health(self, *, timeout=5.0):
        return ProviderHealth(self.name, True, latency_ms=1.0)


def test_provider_registry_registers_and_creates_adapter():
    registry = ProviderRegistry()
    registry.register("dummy", DummyProvider)
    assert registry.names() == ["dummy"]
    adapter = registry.create("dummy", value="ready")
    assert adapter.name == "dummy"
    assert adapter.chat("hello").text == "ready"
    assert adapter.chat("hello").usage.total_tokens == 3
    assert adapter.capabilities.structured_output is True


def test_provider_registry_normalizes_unknown_and_invalid_registration():
    registry = ProviderRegistry()
    try:
        registry.create("missing")
    except ProviderAdapterError as exc:
        assert "Unknown provider adapter" in str(exc)
    else:
        raise AssertionError("unknown provider must fail")

    try:
        registry.register("", DummyProvider)
    except ValueError:
        pass
    else:
        raise AssertionError("empty provider name must fail")

    try:
        registry.register("invalid", object())
    except TypeError:
        pass
    else:
        raise AssertionError("non-callable factory must fail")
