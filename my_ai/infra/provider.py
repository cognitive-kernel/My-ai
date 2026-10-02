from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol
import sys


class ProviderAdapterError(RuntimeError):
    """Normalized provider error exposed above provider-specific adapters."""


@dataclass(frozen=True)
class ProviderCapabilities:
    chat: bool = True
    streaming: bool = False
    structured_output: bool = False
    embeddings: bool = False
    reasoning: bool = False
    health_check: bool = True


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    available: bool
    latency_ms: float | None = None
    version: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class ProviderResponse:
    text: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Any = None


class LLMProviderAdapter(Protocol):
    """Stable contract between Agent/runtime code and an LLM provider."""

    name: str
    capabilities: ProviderCapabilities

    def chat(self, message: str, *, system: str | None = None, history: list[dict[str, str]] | None = None) -> ProviderResponse:
        ...

    def stream_chat(
        self,
        message: str,
        *,
        system: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        ...

    def structured_chat_json(
        self,
        message: str,
        schema: dict[str, Any],
        *,
        system: str | None = None,
    ) -> dict[str, Any]:
        ...

    def health(self, *, timeout: float = 5.0) -> ProviderHealth:
        ...


class ProviderRegistry:
    """Runtime registry for provider adapters; no provider is hard-coded into Agent logic."""

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}

    def register(self, name: str, factory: Any) -> None:
        key = str(name).strip()
        if not key:
            raise ValueError("Provider name is required.")
        if not callable(factory):
            raise TypeError("Provider factory must be callable.")
        self._factories[key] = factory

    def names(self) -> list[str]:
        return sorted(self._factories)

    def create(self, name: str, **kwargs: Any) -> LLMProviderAdapter:
        key = str(name).strip()
        factory = self._factories.get(key)
        if factory is None:
            raise ProviderAdapterError(f"Unknown provider adapter: {key}")
        try:
            return factory(**kwargs)
        except ProviderAdapterError:
            raise
        except Exception as exc:
            raise ProviderAdapterError(f"Provider adapter initialization failed: {key}: {exc}") from exc


# Compatibility bridge for the existing llm module, which resolves ProviderRegistry
# as a module-global name after importing ProviderCapabilities from this module.
_llm_module = sys.modules.get("my_ai.infra.llm")
if _llm_module is not None:
    setattr(_llm_module, "ProviderRegistry", ProviderRegistry)
