"""Infrastructure adapters: LLM, persistence, network and external systems."""

# Centralize the custom-provider contract at the public infrastructure boundary.
# This keeps direct imports of my_ai.infra.llm subject to the same validation as the facade.
from . import llm as _llm

_original_create_llm = _llm.create_llm

def _validated_create_llm(*args, **kwargs):
    provider = str(_llm._runtime_setting("llm.provider", getattr(_llm._settings(), "llm_provider", "auto")) or "auto")
    if provider == "custom-openai-compatible":
        base_url = str(_llm._runtime_setting("llm.custom.base_url", "") or "").strip()
        if not base_url:
            raise _llm.LLMError("Custom LLM provider requires a base URL.")
    return _original_create_llm(*args, **kwargs)

_llm.create_llm = _validated_create_llm
