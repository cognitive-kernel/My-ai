from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


def _auth_headers(key: str) -> dict[str, str]:
    value = str(get_setting(key, ""))
    return {"Authorization": f"Bearer {value}"} if value else {}

import httpx

from .config import settings
from .settings_store import get_setting
from .provider_catalog import list_providers, list_models


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
        items = [
            {"provider": "ollama", "role": "general", "model": settings.ollama_model},
            {"provider": "ollama", "role": "routing", "model": settings.routing_model},
            {"provider": "ollama", "role": "coding", "model": settings.coding_model},
            {"provider": "ollama", "role": "fallback", "model": settings.fallback_model},
            {"provider": "ollama", "role": "embedding", "model": settings.embedding_model},
            {"provider": "openai-compatible", "role": "general", "model": settings.openai_model},
        ]
        provider = str(get_setting("llm.provider", settings.llm_provider))
        custom_model = str(get_setting("llm.custom.model", "")).strip()
        if provider == "custom-openai-compatible" and custom_model:
            items.append({"provider": "custom-openai-compatible", "role": "general", "model": custom_model})
        try:
            providers = {int(item["id"]): item for item in list_providers(include_disabled=False)}
            for model in list_models(include_disabled=False):
                provider_item = providers.get(int(model["provider_id"]))
                if provider_item and provider_item["enabled"]:
                    items.append({
                        "provider": provider_item["name"],
                        "role": "general",
                        "model": model["model_id"],
                        "version": model.get("version", ""),
                        "context_length": model.get("context_length"),
                        "priority": model.get("priority", 100),
                        "capabilities": provider_item.get("capabilities", {}),
                    })
        except Exception:
            # Catalog is optional during first boot; legacy inventory remains usable.
            pass
        return items

    def _provider_for_model(self, model: str) -> str:
        for item in self.inventory():
            if item["model"] == model:
                return item["provider"]
        return "ollama"

    def health(self, model: str, *, provider: str | None = None, timeout: float = 5.0) -> ModelStatus:
        provider = provider or self._provider_for_model(model)
        started = time.perf_counter()
        try:
            if provider == "custom-openai-compatible":
                base_url = str(get_setting("llm.custom.base_url", "")).rstrip("/")
                if not base_url:
                    return ModelStatus(provider, model, False, (time.perf_counter() - started) * 1000, "custom provider endpoint is not configured")
                response = httpx.get(f"{base_url}/models", headers=_auth_headers("llm.custom.api_key"), timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                models = {str(item.get("id")) for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")}
                available = model in models if models else True
                return ModelStatus(provider, model, available, (time.perf_counter() - started) * 1000)
            response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=timeout)
            response.raise_for_status()
            models = {str(item.get("name")) for item in response.json().get("models", []) if item.get("name")}
            return ModelStatus(provider, model, model in models, (time.perf_counter() - started) * 1000)
        except Exception as exc:
            return ModelStatus(provider, model, False, (time.perf_counter() - started) * 1000, str(exc))

    def health_all(self, *, timeout: float = 5.0) -> list[ModelStatus]:
        unique = list(dict.fromkeys((item["provider"], item["model"]) for item in self.inventory()))
        return [self.health(model, provider=provider, timeout=timeout) for provider, model in unique]

    def available_models(self, *, timeout: float = 5.0) -> set[str]:
        return {status.model for status in self.health_all(timeout=timeout) if status.available}

    def fallback_chain(self, requested: str, *, timeout: float = 5.0) -> list[str]:
        available = self.available_models(timeout=timeout)
        candidates = [item["model"] for item in self.inventory()]
        return list(dict.fromkeys(model for model in candidates if model and model != requested and model in available))

    def choose_fallback(self, requested: str, *, timeout: float = 5.0) -> str | None:
        chain = self.fallback_chain(requested, timeout=timeout)
        return chain[0] if chain else None

    def route_snapshot(self, requested: str, *, timeout: float = 5.0) -> dict[str, Any]:
        status = self.health(requested, timeout=timeout)
        return {"requested": requested, "requested_available": status.available, "requested_error": status.error, "fallback_chain": self.fallback_chain(requested, timeout=timeout)}

    def snapshot(self, *, timeout: float = 5.0) -> dict[str, Any]:
        statuses = self.health_all(timeout=timeout)
        return {
            "inventory": self.inventory(),
            "health": [status.__dict__ for status in statuses],
            "available": sorted(status.model for status in statuses if status.available),
        }
