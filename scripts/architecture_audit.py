from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "my_ai"
SENSITIVE = {"auth.py", "access_policy.py", "self_update.py", "self_repair.py", "watchdog.py", "decision_log.py", "platform.py", "scheduler.py", "infra/persistence.py"}


def scan() -> dict[str, list[str]]:
    unresolved: list[str] = []
    silent: list[str] = []
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.Pass) and (path.name in SENSITIVE or str(path.relative_to(ROOT)) in SENSITIVE):
                    silent.append(f"{path}:{node.lineno}")
            if isinstance(node, ast.Name) and node.id == "NotImplemented":
                unresolved.append(f"{path}:{node.lineno}")
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(marker in line for marker in ("TODO", "FIXME", "HACK", "XXX")):
                unresolved.append(f"{path}:{lineno}")
    return {"unresolved": sorted(set(unresolved)), "silent": sorted(set(silent))}


def main() -> int:
    result = scan()
    if result["unresolved"] or result["silent"]:
        print(result)
        return 1
    print("architecture/silent-failure audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
