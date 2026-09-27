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
