from pathlib import Path
import ast

ROOT = Path(__file__).parents[1] / "my_ai"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                prefix = "." * node.level
                result.add(prefix + node.module)
            elif node.level:
                result.add("." * node.level)
    return result


def test_domain_only_depends_on_core_and_stdlib():
    for path in (ROOT / "domain").glob("*.py"):
        imports = imported_modules(path)
        assert not any(item.startswith("..api") or item.startswith("..infra") or item.startswith("..application") for item in imports)
        assert not any(item in {"..llm", "..db", "..config"} for item in imports)


def test_core_has_no_application_or_infrastructure_dependencies():
    for path in (ROOT / "core").glob("*.py"):
        imports = imported_modules(path)
        assert not any(item.startswith(".") and any(x in item for x in ("application", "domain", "infra", "api")) for item in imports)


def test_application_does_not_import_api_or_ui():
    for path in (ROOT / "application").glob("*.py"):
        imports = imported_modules(path)
        assert not any("api" in item or "static" in item or "ui" in item for item in imports)


def test_infra_does_not_depend_on_api_or_application():
    for path in (ROOT / "infra").glob("*.py"):
        imports = imported_modules(path)
        assert not any(item.startswith("..api") or item.startswith("..application") for item in imports)


def test_critical_flat_modules_are_only_compatibility_facades():
    assert "class OllamaClient" not in (ROOT / "llm.py").read_text(encoding="utf-8")
    assert "def classify(" not in (ROOT / "router.py").read_text(encoding="utf-8")
    assert "def connect(" not in (ROOT / "db.py").read_text(encoding="utf-8")
