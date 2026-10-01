from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

SUITE_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / "personal_agent_suite.json"


def load_suite(path: Path = SUITE_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("suites"), dict):
        raise ValueError("benchmark suite must contain a suites object")
    return data


def validate_suite(path: Path = SUITE_PATH) -> dict[str, Any]:
    data = load_suite(path)
    suites = data["suites"]
    total = 0
    invalid: list[str] = []
    for suite_name, cases in suites.items():
        if not isinstance(cases, list):
            invalid.append(str(suite_name))
            continue
        for index, case in enumerate(cases):
            total += 1
            if not isinstance(case, dict) or not case.get("name"):
                invalid.append(f"{suite_name}[{index}]")
    return {"valid": not invalid, "suite_count": len(suites), "case_count": total, "invalid": invalid}


def run_suite() -> dict[str, object]:
    suite = load_suite()
    results: list[dict[str, object]] = []
    for group, cases in suite["suites"].items():
        for case in cases:
            name = str(case["name"])
            status = "ready"
            details: dict[str, object] = {}
            if group == "retrieval":
                from .memory import recall
                hits = recall(str(case.get("input") or ""), 3)
                expected = str(case.get("expected") or "")
                passed = bool(hits) if expected == "knowledge" else (not hits or any(h.get("hybrid_score", 0) > 0 for h in hits))
                status = "passed" if passed else "failed"
                details = {"hits": len(hits)}
            elif group == "software":
                language = str(case.get("language") or "")
                if language == "Python":
                    tool = shutil.which("python") or shutil.which("python3")
                elif language == "PHP":
                    tool = shutil.which("php")
                elif language == "Web":
                    tool = shutil.which("node")
                else:
                    tool = None
                status = "passed" if tool else "blocked"
                details = {"tool": tool, "acceptance": case.get("acceptance", [])}
            else:
                status = "ready"
                details = {"acceptance": case.get("acceptance", []), "note": "scenario requires a live agent run"}
            results.append({"suite": group, "case": name, "status": status, "details": details})
    return {
        "valid": validate_suite()["valid"],
        "total": len(results),
        "passed": sum(r["status"] == "passed" for r in results),
        "blocked": sum(r["status"] == "blocked" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
        "results": results,
    }
