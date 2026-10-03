#!/usr/bin/env python3
"""Inventory mutable hard-coded configuration candidates for migration into the registry."""
from __future__ import annotations

import ast
import json
import pathlib
import re

_ENV_NAME = re.compile(r"^(?:[A-Z][A-Z0-9_]+)$")
_CATEGORIES = {
    "provider_model": re.compile(r"(provider|model)", re.I),
    "url": re.compile(r"(url|uri|endpoint|host)", re.I),
    "timeout_retry_limit": re.compile(r"(timeout|retry|retries|limit|max|min|delay|backoff)", re.I),
    "feature_flag": re.compile(r"(feature|flag|enabled|enable|disabled)", re.I),
    "policy": re.compile(r"policy", re.I),
    "filesystem_path": re.compile(r"(path|file|dir|directory|workspace|root)", re.I),
    "schedule_interval": re.compile(r"(schedule|interval|cron|period)", re.I),
}


def _targets(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        result = []
        for target in targets:
            if isinstance(target, ast.Name):
                result.append(target.id)
        return result
    return []


def _value(node: ast.AST) -> object:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
        return node.value
    return None


def _category(name: str, value: object) -> str | None:
    for category, pattern in _CATEGORIES.items():
        if pattern.search(name):
            return category
    if isinstance(value, str) and re.match(r"https?://", value):
        return "url"
    return None


def scan(root: str | pathlib.Path = "my_ai") -> list[dict[str, object]]:
    root_path = pathlib.Path(root)
    findings: list[dict[str, object]] = []
    for path in sorted(root_path.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "os" and node.func.attr == "getenv":
                        key = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
                        findings.append({
                            "file": str(path),
                            "line": node.lineno,
                            "kind": "env",
                            "name": key if isinstance(key, str) else None,
                            "value": node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None,
                        })
                for keyword in node.keywords:
                    if keyword.arg and (value := _value(keyword.value)) is not None:
                        category = _category(keyword.arg, value)
                        if category:
                            findings.append({
                                "file": str(path),
                                "line": node.lineno,
                                "kind": category,
                                "name": keyword.arg,
                                "value": str(value)[:200],
                            })

            for name in _targets(node):
                value_node = node.value if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) else None
                value = _value(value_node) if value_node is not None else None
                if value is None:
                    continue
                category = _category(name, value)
                if category:
                    findings.append({
                        "file": str(path),
                        "line": node.lineno,
                        "kind": category,
                        "name": name,
                        "value": str(value)[:200],
                    })

            if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.match(r"https?://", node.value):
                findings.append({
                    "file": str(path),
                    "line": node.lineno,
                    "kind": "url",
                    "name": None,
                    "value": node.value[:200],
                })

    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for item in findings:
        key = (item["file"], item["line"], item["kind"], item.get("name"), item.get("value"))
        unique[key] = item
    return list(unique.values())


if __name__ == "__main__":
    print(json.dumps(scan(), ensure_ascii=False, indent=2, sort_keys=True))
