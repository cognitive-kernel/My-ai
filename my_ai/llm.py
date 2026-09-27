"""Compatibility facade; LLM implementations live in my_ai.infra.llm."""
import httpx
from .config import settings
from .infra.llm import LLMError, HistoryMessage, OllamaClient, OpenAICompatibleClient, create_llm

__all__ = ["LLMError", "HistoryMessage", "OllamaClient", "OpenAICompatibleClient", "create_llm", "httpx", "settings"]
