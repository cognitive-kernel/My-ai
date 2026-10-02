from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class EvalCase:
    query: str
    expected_topics: tuple[str, ...]
    language: str = "en"

def reciprocal_rank(items: Iterable[dict], expected_topics: tuple[str, ...]) -> float:
    for index, item in enumerate(items, 1):
        topic = str(item.get("topic") or "")
        if any(expected.casefold() in topic.casefold() for expected in expected_topics):
            return 1.0 / index
    return 0.0

def run_retrieval_eval(retriever: Callable[[str, int], list[dict]], cases: Iterable[EvalCase]) -> dict:
    cases = tuple(cases)
    results = []
    scores = []
    for case in cases:
        items = retriever(case.query, 5)
        rr = reciprocal_rank(items, case.expected_topics)
        scores.append(rr)
        results.append({"query": case.query, "language": case.language, "mrr_component": rr, "passed": rr > 0, "top": items[0] if items else None})
    passed = sum(1 for score in scores if score > 0)
    return {
        "cases": results,
        "mrr": sum(scores) / len(scores) if scores else 0.0,
        "baseline_cases": len(results),
        "passed": passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "languages": sorted({case.language for case in cases}),
    }

BASELINE_CASES = (
    EvalCase("Python list tuple", ("Python",), "en"),
    EvalCase("SQL Server index execution plan", ("SQL Server",), "en"),
    EvalCase("امنیت پن تست", ("Pentest",), "fa"),
    EvalCase("چطور در پایتون تست واحد بنویسم؟", ("Python",), "fa"),
    EvalCase("مدیریت حافظه در Rust", ("Rust",), "fa"),
    EvalCase("جستجوی ایندکس در SQL Server", ("SQL Server",), "fa"),
    EvalCase("تحلیل امنیت API", ("Pentest",), "fa"),
    EvalCase("JavaScript async await", ("JavaScript",), "en"),
    EvalCase("C pointer memory", ("C",), "en"),
    EvalCase("Kotlin Android activity", ("Android",), "en"),
)


@dataclass(frozen=True)
class ResponseEvalCase:
    prompt: str
    required_markers: tuple[str, ...]
    language: str = "fa"


PERSIAN_RESPONSE_BASELINE = (
    ResponseEvalCase("تفاوت list و tuple در پایتون چیست؟", ("list", "tuple"), "fa"),
    ResponseEvalCase("چطور در پایتون تست واحد بنویسم؟", ("تست", "pytest"), "fa"),
    ResponseEvalCase("ایندکس در SQL Server چه کاربردی دارد؟", ("ایندکس",), "fa"),
    ResponseEvalCase("امنیت API را چگونه بررسی کنم؟", ("امنیت", "API"), "fa"),
)


def _persian_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    persian = sum("؀" <= ch <= "ۿ" for ch in letters)
    return persian / len(letters)


def score_response(response: str, case: ResponseEvalCase) -> dict:
    text = str(response or "").strip()
    folded = text.casefold()
    marker_hits = sum(1 for marker in case.required_markers if marker.casefold() in folded)
    marker_score = marker_hits / len(case.required_markers) if case.required_markers else 1.0
    language_score = min(1.0, _persian_ratio(text) / 0.35) if case.language == "fa" else 1.0
    structure_score = 1.0 if len(text) >= 40 and ("." in text or "؟" in text or "\n" in text) else 0.0
    unknown_penalty = 0.35 if "__MYAI_UNKNOWN__" in text else 0.0
    score = max(0.0, min(1.0, 0.65 * marker_score + 0.25 * language_score + 0.10 * structure_score - unknown_penalty))
    return {
        "prompt": case.prompt,
        "language": case.language,
        "marker_score": round(marker_score, 4),
        "language_score": round(language_score, 4),
        "structure_score": round(structure_score, 4),
        "score": round(score, 4),
        "passed": score >= 0.70 and unknown_penalty == 0.0,
    }


def run_response_eval(responder: Callable[[str], str], cases: Iterable[ResponseEvalCase] = PERSIAN_RESPONSE_BASELINE, baseline: float = 0.70) -> dict:
    cases = tuple(cases)
    results = [score_response(responder(case.prompt), case) for case in cases]
    mean_score = sum(item["score"] for item in results) / len(results) if results else 0.0
    passed = sum(1 for item in results if item["passed"])
    return {
        "cases": results,
        "mean_score": round(mean_score, 4),
        "pass_rate": passed / len(results) if results else 0.0,
        "baseline": float(baseline),
        "baseline_met": mean_score >= float(baseline),
        "case_count": len(results),
    }


@dataclass(frozen=True)
class RegressionThreshold:
    name: str
    minimum: float


DEFAULT_REGRESSION_THRESHOLDS = (
    RegressionThreshold("retrieval_mrr", 0.70),
    RegressionThreshold("persian_response_mean", 0.70),
    RegressionThreshold("citation_coverage", 1.0),
    RegressionThreshold("confidence_calibration", 0.70),
    RegressionThreshold("router_accuracy", 0.90),
    RegressionThreshold("skill_verification", 0.80),
)


def evaluate_regression_metrics(metrics: dict[str, float], thresholds=DEFAULT_REGRESSION_THRESHOLDS) -> dict:
    checks = []
    for threshold in thresholds:
        value = float(metrics.get(threshold.name, 0.0))
        checks.append({
            "name": threshold.name,
            "value": round(value, 6),
            "minimum": threshold.minimum,
            "passed": value >= threshold.minimum,
        })
    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def compare_regression_baseline(current: dict[str, float], baseline: dict[str, float], thresholds=DEFAULT_REGRESSION_THRESHOLDS) -> dict:
    gate = evaluate_regression_metrics(current, thresholds)
    deltas = {
        key: round(float(current.get(key, 0.0)) - float(baseline.get(key, 0.0)), 6)
        for key in set(current) | set(baseline)
    }
    regressions = [
        key for key, delta in deltas.items()
        if delta < 0 and float(current.get(key, 0.0)) < next(
            (t.minimum for t in thresholds if t.name == key), 0.0
        )
    ]
    return {**gate, "baseline": baseline, "current": current, "deltas": deltas, "regressions": sorted(regressions)}


def load_versioned_dataset(path=None) -> dict:
    import json
    from pathlib import Path
    dataset_path = Path(path) if path else Path(__file__).resolve().parents[1] / "evals" / "datasets" / "retrieval_v1.json"
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not str(data.get("version","")).startswith("retrieval-"):
        raise ValueError("Unsupported evaluation dataset version.")
    return data


def metric_thresholds() -> dict[str, float]:
    return {item.name: float(item.minimum) for item in DEFAULT_REGRESSION_THRESHOLDS}


def regression_report(current: dict[str, float], baseline: dict[str, float]) -> dict:
    report = compare_regression_baseline(current, baseline)
    report["thresholds"] = metric_thresholds()
    report["status"] = "passed" if report["passed"] else "failed"
    return report
