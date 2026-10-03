from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CATEGORY_RULES = {
    "provider_model_names": re.compile(
        r"(provider|model|ollama|openai|anthropic|gemini|whisper|tts|embedding|sampler|upscaler)",
        re.I,
    ),
    "urls": re.compile(r"^(https?|wss?)://|(^|_)(url|endpoint|base_url|host)(_|$)", re.I),
    "timeouts_retries_limits": re.compile(
        r"(timeout|retry|backoff|limit|max_|minimum_|maximum_|quota|rate_limit|context_length|steps|cfg)",
        re.I,
    ),
    "feature_flags": re.compile(r"(^|_)(enable|enabled|disable|disabled|feature|flag)(_|$)", re.I),
    "policies": re.compile(r"(policy|approval|authorize|permission|allow|deny|sandbox|security|retention)", re.I),
    "filesystem_paths": re.compile(r"(path|root|dir|directory|folder|storage|backup|upload|download|cache)", re.I),
    "schedules_intervals": re.compile(r"(schedule|interval|cron|period|frequency|review|refresh|poll)", re.I),
}


def _category(name: str) -> str | None:
    for category, pattern in CATEGORY_RULES.items():
        if pattern.search(name):
            return category
    return None


def inventory(root: Path = ROOT) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.py")):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                call_name = ast.unparse(node)
                if node.func.attr in {"getenv", "environ"}:
                    name = (
                        node.args[0].value
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                        else "dynamic"
                    )
                    items.append({
                        "category": "environment",
                        "file": str(path.relative_to(root)),
                        "line": node.lineno,
                        "name": name,
                        "value": None,
                        "source": call_name,
                    })
                    continue
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, (str, int, float, bool)):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                name = target.id
                category = _category(name)
                if category is None:
                    continue
                items.append({
                    "category": category,
                    "file": str(path.relative_to(root)),
                    "line": node.lineno,
                    "name": name,
                    "value": value.value,
                    "source": ast.unparse(node),
                })
    return items


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {name: [] for name in (*CATEGORY_RULES.keys(), "environment")}
    for item in items:
        categories.setdefault(str(item["category"]), []).append(item)
    return {
        "total": len(items),
        "categories": {name: len(values) for name, values in categories.items()},
        "items": items,
    }


def main() -> int:
    print(json.dumps(summarize(inventory()), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
