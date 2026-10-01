from __future__ import annotations

import json
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
