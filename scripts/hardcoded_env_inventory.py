from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(root: Path = ROOT) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.py")):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"getenv", "environ"}:
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "os":
                continue
            key = None
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                key = node.args[0].value
            items.append({"file": str(path.relative_to(root)), "line": node.lineno, "name": key, "call": ast.unparse(node)})
    return items


def main() -> int:
    result = inventory()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
