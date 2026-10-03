from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class ComparisonResult:
    category: str
    passed: bool
    score: float
    differences: list[str]


def compare_routes(reference: Iterable[str], candidate: Iterable[str]) -> ComparisonResult:
    left, right = set(reference), set(candidate)
    missing = sorted(left - right)
    extra = sorted(right - left)
    total = max(1, len(left | right))
    score = len(left & right) / total
    return ComparisonResult("routes", not missing, score, [f"missing:{x}" for x in missing] + [f"extra:{x}" for x in extra])


def compare_contracts(reference: dict[str, Any], candidate: dict[str, Any]) -> ComparisonResult:
    differences = []
    for key in sorted(set(reference) | set(candidate)):
        if reference.get(key) != candidate.get(key):
            differences.append(key)
    total = max(1, len(set(reference) | set(candidate)))
    score = 1.0 - len(differences) / total
    return ComparisonResult("contracts", not differences, max(0.0, score), differences)


def compare_files(reference_root: str | Path, candidate_root: str | Path) -> ComparisonResult:
    ref = Path(reference_root).resolve()
    cand = Path(candidate_root).resolve()
    ref_files = {str(p.relative_to(ref)) for p in ref.rglob("*") if p.is_file()}
    cand_files = {str(p.relative_to(cand)) for p in cand.rglob("*") if p.is_file()}
    differences = [f"missing:{x}" for x in sorted(ref_files - cand_files)]
    differences += [f"extra:{x}" for x in sorted(cand_files - ref_files)]
    score = len(ref_files & cand_files) / max(1, len(ref_files | cand_files))
    return ComparisonResult("files", not (ref_files - cand_files), score, differences)


def compare_screenshot_bytes(reference: bytes, candidate: bytes) -> ComparisonResult:
    left = hashlib.sha256(reference).hexdigest()
    right = hashlib.sha256(candidate).hexdigest()
    passed = left == right
    return ComparisonResult("visual", passed, 1.0 if passed else 0.0, [] if passed else ["screenshot_hash_mismatch"])


def compare_behavior(
    scenarios: Iterable[Any],
    reference_runner: Callable[[Any], Any],
    candidate_runner: Callable[[Any], Any],
) -> ComparisonResult:
    differences = []
    total = 0
    matched = 0
    for scenario in scenarios:
        total += 1
        expected = reference_runner(scenario)
        actual = candidate_runner(scenario)
        if expected == actual:
            matched += 1
        else:
            differences.append({"scenario": scenario, "expected": expected, "actual": actual})
    score = matched / max(1, total)
    return ComparisonResult("behavior", not differences, score, [str(x) for x in differences])


def verify_reproduction(
    specification: dict[str, Any],
    workspace: str | Path,
    *,
    reference_workspace: str | Path | None = None,
    reference_routes: Iterable[str] = (),
    candidate_routes: Iterable[str] = (),
    reference_contracts: dict[str, Any] | None = None,
    candidate_contracts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = [compare_routes(reference_routes, candidate_routes)]
    if reference_workspace is not None:
        checks.insert(0, compare_files(reference_workspace, workspace))
    if reference_contracts is not None and candidate_contracts is not None:
        checks.append(compare_contracts(reference_contracts, candidate_contracts))
    coverage = float(specification.get("coverage", 0.0) or 0.0)
    return {
        "passed": all(x.passed for x in checks),
        "coverage": coverage,
        "checks": [x.__dict__ for x in checks],
        "differences": [d for x in checks for d in x.differences],
    }


def repair_loop(
    current: dict[str, Any],
    repair: Callable[[dict[str, Any]], dict[str, Any]],
    verify: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    max_rounds: int = 3,
) -> dict[str, Any]:
    history = []
    candidate = dict(current)
    for round_no in range(1, max(1, int(max_rounds)) + 1):
        report = verify(candidate)
        history.append({"round": round_no, "verification": report})
        if report.get("passed"):
            return {"passed": True, "rounds": history, "candidate": candidate}
        candidate = repair({"candidate": candidate, "verification": report, "round": round_no})
    final = verify(candidate)
    history.append({"round": len(history) + 1, "verification": final})
    return {"passed": bool(final.get("passed")), "rounds": history, "candidate": candidate}
