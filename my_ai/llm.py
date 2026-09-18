from __future__ import annotations

import httpx

from .config import settings


class LLMError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    def chat(self, message: str, system: str | None = None) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "stream": False,
            "messages": [],
        }
        messages = payload["messages"]
        assert isinstance(messages, list)
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        data = response.json()
        try:
            return str(data["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected Ollama response: {data}") from exc
