from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class EvalCase:
    query: str
    expected_topics: tuple[str, ...]

def reciprocal_rank(items: Iterable[dict], expected_topics: tuple[str, ...]) -> float:
    for index, item in enumerate(items, 1):
        topic = str(item.get("topic") or "")
        if any(expected.casefold() in topic.casefold() for expected in expected_topics):
            return 1.0 / index
    return 0.0

def run_retrieval_eval(retriever: Callable[[str, int], list[dict]], cases: Iterable[EvalCase]) -> dict:
    results = []
    scores = []
    for case in cases:
        items = retriever(case.query, 5)
        rr = reciprocal_rank(items, case.expected_topics)
        scores.append(rr)
        results.append({"query": case.query, "mrr_component": rr, "passed": rr > 0, "top": items[0] if items else None})
    return {
        "cases": results,
        "mrr": sum(scores) / len(scores) if scores else 0.0,
        "baseline_cases": len(results),
    }

BASELINE_CASES = (
    EvalCase("Python list tuple", ("Python",)),
    EvalCase("SQL Server index execution plan", ("SQL Server",)),
    EvalCase("امنیت پن تست", ("Pentest",)),
)
