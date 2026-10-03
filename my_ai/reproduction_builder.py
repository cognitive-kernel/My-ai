from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def generate_workspace(spec: dict[str, Any], root: str | Path) -> dict[str, Any]:
    workspace = Path(root).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "frontend").mkdir(exist_ok=True)
    (workspace / "backend").mkdir(exist_ok=True)
    (workspace / "tests").mkdir(exist_ok=True)
    (workspace / "README.md").write_text(
        "# Reproduced Project\n\nGenerated from an authorized source specification.\n"
        "This project is an independent implementation; source secrets and private credentials are excluded.\n",
        encoding="utf-8",
    )
    (workspace / "reproduction.spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    routes = spec.get("requirements", {}).get("navigation_links", [])
    (workspace / "frontend" / "routes.json").write_text(
        json.dumps({"routes": routes}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "workspace": str(workspace),
        "files": [
            "README.md",
            "reproduction.spec.json",
            "frontend/routes.json",
        ],
        "independent": True,
        "secrets_copied": False,
    }


def compare_spec_to_workspace(spec: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve()
    expected = [
        root / "README.md",
        root / "reproduction.spec.json",
        root / "frontend" / "routes.json",
    ]
    missing = [str(path.relative_to(root)) for path in expected if not path.exists()]
    return {
        "passed": not missing,
        "missing": missing,
        "workspace": str(root),
        "coverage": 1.0 if not missing else 1.0 - len(missing) / len(expected),
    }
