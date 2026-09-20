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


class OpenAICompatibleClient:
    """Optional Responses-API backend; disabled unless LLM_PROVIDER=openai."""

    def __init__(self) -> None:
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model
        self.api_key = settings.openai_api_key
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    def chat(self, message: str, system: str | None = None) -> str:
        payload: dict[str, object] = {"model": self.model, "input": message}
        if system:
            payload["instructions"] = system
        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc

        data = response.json()
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        chunks: list[str] = []
        for item in data.get("output", []) if isinstance(data, dict) else []:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        if chunks:
            return "".join(chunks)
        raise LLMError(f"Unexpected OpenAI response: {data}")


def create_llm():
    if settings.llm_provider in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAICompatibleClient()
    return OllamaClient()
