from pathlib import Path
import ast

ROOT = Path(__file__).parents[1] / "my_ai"

def test_layer_packages_exist():
    for name in ("core", "domain", "infra", "api_layer"):
        assert (ROOT / name).is_dir()

def test_domain_does_not_import_api_or_ui():
    for path in (ROOT / "domain").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(x.name for x in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any("api" in item or "ui" in item for item in imports)
