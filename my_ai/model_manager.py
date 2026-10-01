from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import httpx

from .config import settings


@dataclass(frozen=True)
class ModelStatus:
    provider: str
    model: str
    available: bool
    latency_ms: float | None
    error: str | None = None


class ModelManager:
    """Central model inventory and health checks used by routing/failover."""

    def inventory(self) -> list[dict[str, str]]:
        return [
            {"provider": "ollama", "role": "general", "model": settings.ollama_model},
            {"provider": "ollama", "role": "routing", "model": settings.routing_model},
            {"provider": "ollama", "role": "coding", "model": settings.coding_model},
            {"provider": "ollama", "role": "fallback", "model": settings.fallback_model},
            {"provider": "ollama", "role": "embedding", "model": settings.embedding_model},
            {"provider": "openai-compatible", "role": "general", "model": settings.openai_model},
        ]

    def health(self, model: str, *, timeout: float = 5.0) -> ModelStatus:
        started = time.perf_counter()
        try:
            response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=timeout)
            response.raise_for_status()
            models = {str(item.get("name")) for item in response.json().get("models", []) if item.get("name")}
            return ModelStatus("ollama", model, model in models, (time.perf_counter() - started) * 1000)
        except Exception as exc:
            return ModelStatus("ollama", model, False, (time.perf_counter() - started) * 1000, str(exc))

    def health_all(self, *, timeout: float = 5.0) -> list[ModelStatus]:
        unique = list(dict.fromkeys(item["model"] for item in self.inventory() if item["provider"] == "ollama"))
        return [self.health(model, timeout=timeout) for model in unique]

    def available_models(self, *, timeout: float = 5.0) -> set[str]:
        return {status.model for status in self.health_all(timeout=timeout) if status.available}

    def choose_fallback(self, requested: str, *, timeout: float = 5.0) -> str | None:
        available = self.available_models(timeout=timeout)
        if settings.fallback_model in available and settings.fallback_model != requested:
            return settings.fallback_model
        return None

    def snapshot(self, *, timeout: float = 5.0) -> dict[str, Any]:
        statuses = self.health_all(timeout=timeout)
        return {
            "inventory": self.inventory(),
            "health": [status.__dict__ for status in statuses],
            "available": sorted(status.model for status in statuses if status.available),
        }
