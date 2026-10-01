"""Advanced, dependency-light agent orchestration primitives.

These deterministic controls sit around the LLM: model choice, context budgets,
capabilities, policy, evidence, versioning, traceability, scheduling and evals.
The implementation deliberately uses the standard library for local-first use on
constrained hardware.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
import threading
from typing import Any, Callable, Iterable


class OperationRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


class RuntimeMode(str, Enum):
    OFFLINE = "offline"
    LOCAL = "local"
    ONLINE = "online"


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
    """Select a viable model while respecting capabilities and hardware."""

    def choose(self, models: Iterable[ModelProfile], task: TaskProfile, resources: ResourceSnapshot) -> ModelChoice:
        candidates = [m for m in models if task.required_capabilities <= m.capabilities]
        candidates = [m for m in candidates if m.context_window >= task.context_tokens]
        candidates = [m for m in candidates if m.ram_gb <= resources.ram_available_gb and m.vram_gb <= resources.vram_available_gb]
        if not candidates:
            raise RuntimeError("no model satisfies task capabilities, context, and available resources")
        candidates.sort(key=lambda m: (m.quality * (0.35 + task.complexity), m.speed, -m.ram_gb), reverse=True)
        chosen = candidates[0]
        return ModelChoice(chosen, f"complexity={task.complexity:.2f} ram={resources.ram_available_gb:.1f}GB vram={resources.vram_available_gb:.1f}GB")


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
    @staticmethod
    def compact_text(text: str, max_tokens: int) -> str:
        words = str(text or "").split()
        if len(words) <= max_tokens:
            return str(text or "")
        available = max(2, max_tokens - 3)
        head = max(1, available // 2)
        tail = max(1, available - head)
        return " ".join(words[:head]) + " … [compacted] … " + " ".join(words[-tail:])

    def pack(self, items: Iterable[ContextItem], budget: int) -> ContextPack:
        material = list(items)
        if budget <= 0:
            return ContextPack((), 0, len(material))
        ranked = sorted(material, key=lambda x: x.priority, reverse=True)
        selected: list[ContextItem] = []
        used = omitted = 0
        for item in ranked:
            tokens = item.tokens if item.tokens is not None else max(1, len(item.text.split()))
            if used + tokens <= budget:
                selected.append(item)
                used += tokens
                continue
            remaining = budget - used
            if remaining >= 5:
                compacted = self.compact_text(item.text, remaining)
                compacted_tokens = max(1, len(compacted.split()))
                if compacted_tokens <= remaining:
                    selected.append(ContextItem(item.kind, compacted, item.priority, compacted_tokens))
                    used += compacted_tokens
                    continue
            omitted += 1
        return ContextPack(tuple(selected), used, omitted)


@dataclass(frozen=True)
class Capability:
    name: str
    risk: OperationRisk
    enabled: bool = True
    requires_approval: bool = False
    offline: bool = True


class CapabilityRegistry:
    def __init__(self, capabilities: Iterable[Capability] = ()) -> None:
        self._items = {c.name: c for c in capabilities}

    def register(self, capability: Capability) -> None:
        self._items[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._items.get(name)

    def all(self) -> tuple[Capability, ...]:
        return tuple(self._items.values())


@dataclass
class PolicyEngine:
    capabilities: dict[str, Capability] = field(default_factory=dict)

    def authorize(self, name: str, *, approved: bool = False, mode: RuntimeMode = RuntimeMode.LOCAL) -> None:
        cap = self.capabilities.get(name)
        if cap is None or not cap.enabled:
            raise PermissionError(f"capability disabled: {name}")
        if mode is RuntimeMode.ONLINE and not cap.offline and not approved:
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
        items = self.for_claim(claim)
        return len({e.claim.casefold() for e in items}) > 1


@dataclass(frozen=True)
class KnowledgeVersion:
    key: str
    version: int
    content: str
    source: str
    active: bool = True


class KnowledgeVersionStore:
    def __init__(self) -> None:
        self._items: dict[str, list[KnowledgeVersion]] = {}

    def add(self, key: str, content: str, source: str) -> KnowledgeVersion:
        history = self._items.setdefault(key, [])
        for old in history:
            object.__setattr__(old, "active", False)
        item = KnowledgeVersion(key, len(history) + 1, content, source)
        history.append(item)
        return item

    def active(self, key: str) -> KnowledgeVersion | None:
        history = self._items.get(key, [])
        return next((item for item in reversed(history) if item.active), None)

    def history(self, key: str) -> tuple[KnowledgeVersion, ...]:
        return tuple(self._items.get(key, ()))


@dataclass(frozen=True)
class TraceNode:
    node_id: str
    kind: str
    value: str


class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, TraceNode] = {}
        self.edges: set[tuple[str, str, str]] = set()

    def add_node(self, node: TraceNode) -> None:
        self.nodes[node.node_id] = node

    def link(self, source: str, relation: str, target: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("trace edge requires existing nodes")
        self.edges.add((source, relation, target))


@dataclass
class ResourceScheduler:
    max_concurrent: int = 1
    _active: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def acquire(self) -> bool:
        with self._lock:
            if self._active >= self.max_concurrent:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)


@dataclass(frozen=True)
class CompletionReport:
    goal: str
    requirements: tuple[str, ...]
    validation: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return bool(self.goal) and bool(self.requirements) and bool(self.validation) and not self.unresolved


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
    def run(self, cases: Iterable[EvalCase], evaluator: Callable[[str], Any]) -> list[EvalResult]:
        results: list[EvalResult] = []
        for case in cases:
            started = monotonic()
            try:
                actual = str(evaluator(case.input))
                passed = actual == case.expected
                detail = "" if passed else f"expected={case.expected!r} actual={actual!r}"
            except Exception as exc:
                passed = False
                detail = f"{type(exc).__name__}: {exc}"
            results.append(EvalResult(case.name, passed, int((monotonic() - started) * 1000), detail))
        return results


__all__ = [
    "Capability", "CapabilityRegistry", "CompletionReport", "ContextBudgetManager", "ContextItem", "ContextPack",
    "EvalCase", "EvalResult", "EvaluationHarness", "Evidence", "EvidenceGraph", "EvidenceStore",
    "KnowledgeVersion", "KnowledgeVersionStore", "ModelChoice", "ModelProfile", "ModelRouter", "OperationRisk",
    "PolicyEngine", "ResourceScheduler", "ResourceSnapshot", "RuntimeMode", "TaskProfile", "TraceNode",
]
