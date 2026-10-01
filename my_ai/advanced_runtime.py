"""Runtime adapter for the advanced deterministic agent controls.

This module is intentionally side-effect free: it does not mutate the existing
SQLite knowledge store, conversation state, backups, or model configuration.
It provides a safe integration boundary for the main runtime to adopt the new
controls incrementally without risking persisted user data.
"""
from __future__ import annotations

from dataclasses import dataclass

from .advanced_agent import (
    Capability,
    CapabilityRegistry,
    ContextBudgetManager,
    ContextItem,
    ModelProfile,
    ModelRouter,
    PolicyEngine,
    ResourceSnapshot,
    RuntimeMode,
    TaskProfile,
)


@dataclass(frozen=True)
class RuntimeResources:
    """Conservative resource view used when exact telemetry is unavailable."""

    ram_available_gb: float
    vram_available_gb: float = 0.0
    cpu_percent: float = 0.0


def detect_resources() -> RuntimeResources:
    """Return a safe resource estimate without requiring third-party packages."""
    try:
        import psutil  # type: ignore
    except ImportError:
        return RuntimeResources(ram_available_gb=0.0)
    memory = psutil.virtual_memory()
    return RuntimeResources(
        ram_available_gb=memory.available / (1024**3),
        cpu_percent=float(psutil.cpu_percent(interval=None)),
    )


class AdvancedRuntime:
    """Non-destructive orchestration facade for incremental runtime adoption."""

    def __init__(self, *, mode: RuntimeMode = RuntimeMode.LOCAL) -> None:
        self.mode = mode
        self.models: list[ModelProfile] = []
        self.capabilities = CapabilityRegistry()
        self.policy = PolicyEngine({})
        self.context = ContextBudgetManager()
        self.router = ModelRouter()

    def register_model(self, model: ModelProfile) -> None:
        self.models.append(model)

    def register_capability(self, capability: Capability) -> None:
        self.capabilities.register(capability)
        self.policy.capabilities[capability.name] = capability

    def choose_model(self, task: TaskProfile, resources: RuntimeResources | None = None):
        snapshot = resources or detect_resources()
        return self.router.choose(
            self.models,
            task,
            ResourceSnapshot(
                ram_available_gb=snapshot.ram_available_gb,
                vram_available_gb=snapshot.vram_available_gb,
                cpu_percent=snapshot.cpu_percent,
            ),
        )

    def authorize(self, capability: str, *, approved: bool = False) -> None:
        self.policy.authorize(capability, approved=approved, mode=self.mode)

    def pack_context(self, items: list[ContextItem], budget: int):
        return self.context.pack(items, budget)


__all__ = ["AdvancedRuntime", "RuntimeResources", "detect_resources"]
