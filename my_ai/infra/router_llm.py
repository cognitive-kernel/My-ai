from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..config import settings
from ..metrics import record_error, record_inference
from .llm import LLMError, OllamaClient, OpenAICompatibleClient


class OpenAIStructuredRouterClient(OpenAICompatibleClient):
    """OpenAI Responses adapter using strict JSON Schema structured output."""

    def structured_chat_json(self, message: str, schema: dict[str, Any], system: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": [{"role": "user", "content": message}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "route_request",
                    "description": "Strict semantic routing result. Never grants permission.",
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        if system:
            payload["instructions"] = system
        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") if isinstance(data, dict) else {}
            record_inference(
                "openai", self.model, time.perf_counter() - started,
                prompt_tokens=(usage or {}).get("input_tokens"), output_tokens=(usage or {}).get("output_tokens"),
            )
            raw = data.get("output_text") if isinstance(data, dict) else None
            if not isinstance(raw, str):
                chunks: list[str] = []
                for item in data.get("output", []) if isinstance(data, dict) else []:
                    for content in item.get("content", []) if isinstance(item, dict) else []:
                        if isinstance(content, dict) and isinstance(content.get("text"), str):
                            chunks.append(content["text"])
                raw = "".join(chunks) if chunks else None
            if not isinstance(raw, str):
                raise LLMError("Structured OpenAI response has no output text.")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise LLMError("Structured OpenAI response is not an object.")
            return parsed
        except (httpx.HTTPError, json.JSONDecodeError, LLMError) as exc:
            record_error("openai", self.model)
            raise LLMError(f"Structured OpenAI request failed: {exc}") from exc


def create_structured_router() -> Any:
    """Return the provider adapter used exclusively by the semantic router."""
    provider = settings.llm_provider
    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAIStructuredRouterClient()
    if provider == "auto" and settings.openai_api_key and not getattr(settings, "offline_strict", False):
        return OpenAIStructuredRouterClient()
    return OllamaClient(task="routing")
