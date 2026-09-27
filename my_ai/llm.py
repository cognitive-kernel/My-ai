"""Compatibility facade; LLM implementations live in my_ai.infra.llm."""
import httpx
from .config import settings
from .infra import llm as _impl

LLMError = _impl.LLMError
HistoryMessage = _impl.HistoryMessage


class OllamaClient(_impl.OllamaClient):
    def __init__(self, task=None):
        _impl.settings = settings
        super().__init__(task=task)


class OpenAICompatibleClient(_impl.OpenAICompatibleClient):
    def __init__(self):
        _impl.settings = settings
        super().__init__()


def create_llm(task=None):
    _impl.settings = settings
    provider = getattr(settings, "llm_provider", "auto")
    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAICompatibleClient()
    if provider == "auto" and getattr(settings, "openai_api_key", "") and not getattr(settings, "offline_strict", False):
        return OpenAICompatibleClient()
    return OllamaClient(task=task)


__all__ = ["LLMError", "HistoryMessage", "OllamaClient", "OpenAICompatibleClient", "create_llm", "httpx", "settings"]
