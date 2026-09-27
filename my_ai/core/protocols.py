from __future__ import annotations

from typing import Any, Iterator, Protocol, Sequence


class LLM(Protocol):
    def chat(self, message: str, system: str | None = None, history: Sequence[dict[str, str]] | None = None) -> str: ...
    def stream_chat(self, message: str, system: str | None = None, history: Sequence[dict[str, str]] | None = None) -> Iterator[str]: ...


class StructuredRouter(Protocol):
    def structured_chat_json(
        self,
        message: str,
        schema: dict[str, Any],
        system: str | None = None,
    ) -> dict[str, Any]: ...


class Retriever(Protocol):
    def recall(self, query: str, limit: int = 8) -> list[dict]: ...


class Policy(Protocol):
    def enforce(self, **kwargs): ...
