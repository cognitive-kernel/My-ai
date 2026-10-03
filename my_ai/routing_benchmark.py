from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class RoutingCase:
    prompt: str
    expected_intent: str
    task: str
    complexity: float = 0.5


DEFAULT_CASES = (
    RoutingCase("سلام", "chat", "chat", 0.1),
    RoutingCase("یک برنامه Python بنویس", "coding", "coding", 0.6),
    RoutingCase("قیمت EURUSD الان چنده؟", "metatrader", "market", 0.7),
    RoutingCase("RSI EURUSD الان چند است؟", "metatrader", "market", 0.8),
    RoutingCase("برای MT4 یک indicator بنویس", "coding", "coding", 0.7),
    RoutingCase("بازار را با EURUSD و RSI و MACD تحلیل کن", "metatrader", "reasoning", 0.95),
)


def benchmark_router(router: Callable[[str], Any], cases: Iterable[RoutingCase] = DEFAULT_CASES) -> dict[str, Any]:
    rows = []
    for case in cases:
        started = perf_counter()
        result = router(case.prompt)
        elapsed_ms = (perf_counter() - started) * 1000
        intent = str(getattr(result, "name", result.get("intent") if isinstance(result, dict) else result))
        rows.append({
            "prompt": case.prompt,
            "expected": case.expected_intent,
            "actual": intent,
            "correct": intent == case.expected_intent,
            "latency_ms": round(elapsed_ms, 3),
            "task": case.task,
            "complexity": case.complexity,
        })
    correct = sum(1 for row in rows if row["correct"])
    return {
        "cases": rows,
        "accuracy": correct / len(rows) if rows else 0.0,
        "mean_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 3) if rows else 0.0,
        "case_count": len(rows),
    }


def benchmark_model_selection(
    selector: Callable[[str], str | None],
    cases: Iterable[RoutingCase] = DEFAULT_CASES,
) -> dict[str, Any]:
    rows = []
    for case in cases:
        started = perf_counter()
        model = selector(case.task)
        elapsed_ms = (perf_counter() - started) * 1000
        rows.append({
            "prompt": case.prompt,
            "task": case.task,
            "complexity": case.complexity,
            "model": model,
            "selection_latency_ms": round(elapsed_ms, 3),
            "available": model is not None,
        })
    available = sum(1 for row in rows if row["available"])
    return {
        "cases": rows,
        "availability_rate": available / len(rows) if rows else 0.0,
        "mean_selection_latency_ms": round(
            sum(row["selection_latency_ms"] for row in rows) / len(rows), 3
        ) if rows else 0.0,
        "case_count": len(rows),
    }


def compare_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "accuracy_delta": float(current.get("accuracy", 0.0)) - float(baseline.get("accuracy", 0.0)),
        "latency_delta_ms": float(current.get("mean_latency_ms", 0.0)) - float(baseline.get("mean_latency_ms", 0.0)),
        "current": current,
        "baseline": baseline,
    }
