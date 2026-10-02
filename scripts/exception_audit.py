from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "my_ai"


def audit(root: Path = ROOT) -> list[dict[str, object]]:
    findings = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8-sig")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = node.body
            meaningful = any(
                not isinstance(statement, ast.Pass)
                and not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) and statement.value.value is None)
                for statement in body
            )
            if not meaningful:
                # A documented deliberate suppression for optional/legacy startup paths
                # may place its explanation immediately after `except`; inspect both sides.
                prior = "\n".join(lines[max(0, node.lineno - 4):node.lineno]).casefold()
                following = "\n".join(lines[node.lineno:min(len(lines), node.lineno + 4)]).casefold()
                context = prior + "\n" + following
                if any(marker in context for marker in ("optional", "legacy", "intentional", "deliberate suppression")):
                    meaningful = True
            findings.append({
                "file": str(path.relative_to(root.parent)),
                "line": node.lineno,
                "exception": ast.unparse(node.type) if node.type else "BaseException",
                "handled": meaningful,
            })
    return findings


def main() -> int:
    findings = audit()
    risky = [item for item in findings if not item["handled"]]
    print({"handlers": len(findings), "risky": risky})
    return 1 if risky else 0


if __name__ == "__main__":
    raise SystemExit(main())
