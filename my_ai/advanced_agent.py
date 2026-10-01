"""Advanced, dependency-light agent orchestration primitives.

The module intentionally uses only the Python standard library so the local-first
runtime remains usable on constrained machines. It provides deterministic policy
and budgeting primitives around an LLM rather than pretending those decisions
belong to the model itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Iterable


class OperationRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ModelProfile:
    name: str
    context_window: int
    ram_gb: float = 0.0
    vram_gb: float = 0.0
    quality: float = 0.5
    speed: float = 0.5
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ResourceSnapshot:
    ram_available_gb: float
    vram_available_gb: float = 0.0
    cpu_percent: float = 0.0


@dataclass(frozen=True)
class TaskProfile:
    complexity: float = 0.5
    context_tokens: int = 4096
    latency_budget_ms: int = 30_000
    required_capabilities: frozenset[str] = frozenset()
    network_allowed: bool = False


@dataclass(frozen=True)
class ModelChoice:
    model: ModelProfile
    reason: str


class ModelRouter:
    """Select the smallest viable model while respecting task and resources."""

    def choose(self, models: Iterable[ModelProfile], task: TaskProfile, resources: ResourceSnapshot) -> ModelChoice:
        candidates = [m for m in models if task.required_capabilities <= m.capabilities]
        candidates = [m for m in candidates if m.context_window >= task.context_tokens]
        candidates = [m for m in candidates if m.ram_gb <= resources.ram_available_gb and m.vram_gb <= resources.vram_available_gb]
        if not candidates:
            raise RuntimeError("no model satisfies task capabilities, context, and available resources")
        candidates.sort(key=lambda m: (m.quality * (0.35 + task.complexity), m.speed, -m.ram_gb), reverse=True)
        chosen = candidates[0]
        return ModelChoice(chosen, f"capabilities={sorted(task.required_capabilities)} complexity={task.complexity:.2f} resources=ram:{resources.ram_available_gb:.1f}GB/vram:{resources.vram_available_gb:.1f}GB")


@dataclass(frozen=True)
class ContextItem:
    kind: str
    text: str
    priority: float = 0.5
    tokens: int | None = None
    provenance: dict[str, Any] | None = None


@dataclass(frozen=True)
class ContextPack:
    items: tuple[ContextItem, ...]
    estimated_tokens: int
    omitted: int


class ContextBudgetManager:
    def pack(self, items: Iterable[ContextItem], budget: int) -> ContextPack:
        if budget <= 0:
            return ContextPack((), 0, len(list(items)))
        ranked = sorted(items, key=lambda x: x.priority, reverse=True)
        selected: list[ContextItem] = []
        used = 0
        omitted = 0
        for item in ranked:
            tokens = item.tokens if item.tokens is not None else max(1, len(item.text.split()))
            if used + tokens <= budget:
                selected.append(item)
                used += tokens
            else:
                omitted += 1
        return ContextPack(tuple(selected), used, omitted)


@dataclass(frozen=True)
class Capability:
    name: str
    risk: OperationRisk
    enabled: bool = True
    requires_approval: bool = False
    offline: bool = True


@dataclass
class PolicyEngine:
    capabilities: dict[str, Capability] = field(default_factory=dict)

    def authorize(self, name: str, *, approved: bool = False, online: bool = False) -> None:
        cap = self.capabilities.get(name)
        if cap is None or not cap.enabled:
            raise PermissionError(f"capability disabled: {name}")
        if online and not cap.offline and not approved:
            raise PermissionError(f"approval required for online capability: {name}")
        if cap.requires_approval and not approved:
            raise PermissionError(f"approval required: {name}")


@dataclass(frozen=True)
class Evidence:
    claim: str
    source: str
    confidence: float = 0.5
    version: str | None = None
    supersedes: str | None = None


class EvidenceStore:
    def __init__(self) -> None:
        self._items: list[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        self._items.append(evidence)

    def for_claim(self, claim: str) -> list[Evidence]:
        needle = claim.casefold()
        return [e for e in self._items if needle in e.claim.casefold()]

    def conflicts(self, claim: str) -> bool:
        values = {e.claim.casefold() for e in self.for_claim(claim)}
        return len(values) > 1


@dataclass
class ResourceScheduler:
    max_concurrent: int = 1
    _active: int = 0

    def acquire(self) -> bool:
        if self._active >= self.max_concurrent:
            return False
        self._active += 1
        return True

    def release(self) -> None:
        self._active = max(0, self._active - 1)


@dataclass(frozen=True)
class EvalCase:
    name: str
    input: str
    expected: str


@dataclass(frozen=True)
class EvalResult:
    name: str
    passed: bool
    latency_ms: int
    detail: str = ""


class EvaluationHarness:
    def run(self, cases: Iterable[EvalCase], evaluator) -> list[EvalResult]:
        results: list[EvalResult] = []
        for case in cases:
            started = monotonic()
            try:
                actual = str(evaluator(case.input))
                passed = actual == case.expected
                detail = "" if passed else f"expected={case.expected!r} actual={actual!r}"
            except Exception as exc:  # evaluation must report failures, not abort the suite
                passed = False
                detail = f"{type(exc).__name__}: {exc}"
            latency = int((monotonic() - started) * 1000)
            results.append(EvalResult(case.name, passed, latency, detail))
        return results


__all__ = [
    "Capability", "ContextBudgetManager", "ContextItem", "ContextPack", "EvalCase",
    "EvalResult", "EvaluationHarness", "Evidence", "EvidenceStore", "ModelChoice",
    "ModelProfile", "ModelRouter", "OperationRisk", "PolicyEngine", "ResourceScheduler",
    "ResourceSnapshot", "TaskProfile",
]
