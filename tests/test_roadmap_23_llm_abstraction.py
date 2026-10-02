from my_ai.infra.provider import LLMProviderAdapter


def test_llm_provider_adapter_is_defined():
    assert LLMProviderAdapter is not None
    for name in ("chat", "health"):
        assert hasattr(LLMProviderAdapter, name)
