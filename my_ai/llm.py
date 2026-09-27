"""Compatibility facade; LLM implementations live in my_ai.infra.llm."""
from .infra.llm import LLMError, HistoryMessage, OllamaClient, OpenAICompatibleClient, create_llm

__all__ = ["LLMError", "HistoryMessage", "OllamaClient", "OpenAICompatibleClient", "create_llm"]
