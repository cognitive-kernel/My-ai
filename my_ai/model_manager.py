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
from .provider_catalog import list_providers, list_models, list_routing_rules, list_fallback_chain
from .task_budget import choose_task_budget


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

    def select_for_task(self, task: str | None = None, *, timeout: float = 5.0) -> str | None:
        """Select an enabled catalog model by declared task capability and priority."""
        requested = str(task or "general").strip().lower()
        aliases = {
            "chat": {"chat", "general"},
            "coding": {"coding", "code"},
            "reasoning": {"reasoning", "complex", "analysis"},
            "embedding": {"embedding", "embeddings"},
            "routing": {"routing", "classification", "classify"},
        }
        wanted = aliases.get(requested, {requested, "general"})
        task_budget = choose_task_budget(requested)
        if not task_budget["admission"]["allowed"]:
            return None
        catalog = list_models(include_disabled=False)
        providers = {int(p["id"]): p for p in list_providers(include_disabled=False)}
        explicit = [r for r in list_routing_rules(task=requested, include_disabled=False)]
        ranked = []
        for item in catalog:
            provider = providers.get(int(item["provider_id"]))
            if not provider or not provider.get("enabled"):
                continue
            tasks = {str(x).strip().lower() for x in (item.get("tasks") or [])}
            if tasks and not (tasks & wanted):
                continue
            health = self.health(str(item["model_id"]), provider=str(provider["name"]), timeout=timeout)
            if health.available:
                rule_priority = next((int(r.get("priority",100)) for r in explicit if r.get("model_id")==item["model_id"]), None)
                priority = rule_priority if rule_priority is not None else int(item.get("priority", 100))
                latency = float(health.latency_ms or 0)
                limits = item.get("limits") or {}
                cost = float(limits.get("cost_per_1k_tokens", limits.get("cost", 0)) or 0)
                cost_weight = float(get_setting("llm.routing.cost_weight", "0") or 0)
                latency_weight = float(get_setting("llm.routing.latency_weight", "1") or 1)
                quality_weight = float(get_setting("llm.routing.quality_weight", "1") or 1)
                quality = float(limits.get("quality_score", limits.get("quality", 0)) or 0)
                context_length = int(item.get("context_length") or 0)
                required_context = 12000 if requested in {"coding", "reasoning"} else 4096
                resource_penalty = 0 if context_length == 0 or context_length >= required_context else 10000
                score = priority + latency * latency_weight + cost * cost_weight - quality * quality_weight + resource_penalty
                ranked.append((score, str(provider["name"]), str(item["model_id"]), latency))
        if ranked:
            ranked.sort(key=lambda x: (x[0], x[1], x[2]))
            return ranked[0][2]
        return None

    def route_score(self, task: str, model: dict[str, Any], health: ModelStatus, *, complexity: float = 0.5) -> float:
        """Deterministic routing score combining capability, availability, latency, resources and complexity."""
        if not health.available:
            return float("inf")
        limits = model.get("limits") or {}
        context = int(model.get("context_length") or 0)
        required = 12000 if str(task).lower() in {"coding", "reasoning"} else 4096
        if context and context < required:
            return float("inf")
        priority = float(model.get("priority", 100) or 100)
        latency = float(health.latency_ms or 0)
        cost = float(limits.get("cost_per_1k_tokens", limits.get("cost", 0)) or 0)
        quality = float(limits.get("quality_score", limits.get("quality", 0)) or 0)
        capability_bonus = float(limits.get("capability_score", 1.0) or 1.0)
        complexity = max(0.0, min(1.0, float(complexity)))
        latency_weight = float(get_setting("llm.routing.latency_weight", "1") or 1)
        cost_weight = float(get_setting("llm.routing.cost_weight", "0") or 0)
        quality_weight = float(get_setting("llm.routing.quality_weight", "1") or 1)
        complexity_weight = float(get_setting("llm.routing.complexity_weight", "20") or 20)
        return (
            priority
            + latency * latency_weight
            + cost * cost_weight
            - quality * quality_weight
            - capability_bonus * complexity * complexity_weight
        )


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

    def fallback_chain(self, requested: str, *, timeout: float = 5.0, task: str = "general") -> list[str]:
        available = self.available_models(timeout=timeout)
        configured = []
        for name in ("default", "global", "ui"):
            configured.extend(x.get("model_id","") for x in list_fallback_chain(name, task))
        candidates = configured + [item["model"] for item in self.inventory()]
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
