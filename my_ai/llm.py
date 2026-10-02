"""Compatibility facade; LLM implementations live in my_ai.infra.llm."""
import httpx
from .config import settings
from .settings_store import get_setting
from .infra.llm import LLMError, HistoryMessage, OllamaClient, OpenAICompatibleClient, create_llm as _infra_create_llm


def _runtime_setting(key: str, fallback=None):
    try:
        return get_setting(key, fallback)
    except Exception:
        return fallback


def create_llm():
    provider = str(_runtime_setting("llm.provider", getattr(settings, "llm_provider", "auto")) or "auto")
    if provider == "custom-openai-compatible":
        base_url = str(_runtime_setting("llm.custom.base_url", "") or "").strip()
        if not base_url:
            raise LLMError("Custom LLM provider requires a base URL.")
    return _infra_create_llm()


__all__ = ["LLMError", "HistoryMessage", "OllamaClient", "OpenAICompatibleClient", "create_llm", "httpx", "settings", "_runtime_setting"]
