from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Evidence:
    kind: str
    source: str
    passed: bool
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    confidence: float
    evidence: tuple[Evidence, ...]
    reason: str = ""


def verify(
    checks: list[tuple[str, Callable[[], bool]]],
    *,
    source: str = "runtime",
    require_all: bool = True,
) -> VerificationResult:
    evidence: list[Evidence] = []
    for kind, check in checks:
        try:
            passed = bool(check())
            detail = ""
        except Exception as exc:
            passed = False
            detail = f"{type(exc).__name__}: {exc}"
        evidence.append(Evidence(kind=kind, source=source, passed=passed, detail=detail))
    if not evidence:
        return VerificationResult(False, 0.0, (), "no evidence")
    passed_count = sum(item.passed for item in evidence)
    confidence = passed_count / len(evidence)
    passed = all(item.passed for item in evidence) if require_all else any(item.passed for item in evidence)
    return VerificationResult(passed, confidence, tuple(evidence))
