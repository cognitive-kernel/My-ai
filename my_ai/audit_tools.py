from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def find_silent_failures(root: Path = ROOT) -> list[dict[str, Any]]:
    findings=[]
    for path in sorted((root / "my_ai").rglob("*.py")):
        try: tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        except (OSError,SyntaxError) as exc:
            findings.append({"path":str(path.relative_to(root)),"kind":"parse_error","error":str(exc)}); continue
        for node in ast.walk(tree):
            if not isinstance(node,ast.ExceptHandler) or not node.body: continue
            if len(node.body)==1 and isinstance(node.body[0],ast.Pass):
                findings.append({"path":str(path.relative_to(root)),"line":node.lineno,"kind":"except_pass","intentional":False})
            elif all(isinstance(x,ast.Expr) and isinstance(getattr(x,"value",None),ast.Constant) and isinstance(x.value.value,str) for x in node.body):
                findings.append({"path":str(path.relative_to(root)),"line":node.lineno,"kind":"except_docstring_only","intentional":False})
    return findings


def architecture_inventory(root: Path = ROOT) -> dict[str, Any]:
    modules={}
    for path in sorted((root/"my_ai").rglob("*.py")):
        rel=str(path.relative_to(root))
        try:
            tree=ast.parse(path.read_text(encoding="utf-8"),filename=rel)
            imports=[]
            public=[]
            for node in tree.body:
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    imports.append(ast.unparse(node))
                elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and not node.name.startswith("_"):
                    public.append(node.name)
            modules[rel]={"imports":imports,"public_symbols":public}
        except (OSError,SyntaxError) as exc:
            modules[rel]={"error":str(exc)}
    return modules


def api_route_inventory(app) -> list[dict[str, Any]]:
    result=[]
    for route in app.routes:
        methods=sorted(getattr(route,"methods",set()) or [])
        path=getattr(route,"path",None)
        if path: result.append({"path":path,"methods":methods,"name":getattr(route,"name",None)})
    return sorted(result,key=lambda x:(x["path"],x["methods"]))


def configuration_inventory(root: Path = ROOT) -> list[dict[str, str]]:
    result=[]
    pattern=re.compile(r'os\.getenv\(["\']([A-Z][A-Z0-9_]+)["\']')
    for path in sorted((root / 'my_ai').rglob('*.py')):
        try: source=path.read_text(encoding='utf-8')
        except OSError: continue
        for name in sorted(set(pattern.findall(source))): result.append({'path':str(path.relative_to(root)),'environment_variable':name})
    return result

def route_inventory(root: Path = ROOT) -> list[dict[str, str]]:
    result = []
    path = root / "my_ai" / "api.py"
    if not path.exists():
        return result
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return result
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            result.append({"method": decorator.func.attr.upper(), "path": str(decorator.args[0].value)})
    return sorted(result, key=lambda x: (x["path"], x["method"]))

def sensitive_route_inventory(root: Path = ROOT) -> list[dict[str, str]]:
    sensitive = ("/admin", "/tools", "/skills/", "/sessions", "/streams/", "/state/", "/self-repair", "/self-update", "/security")
    return [route for route in route_inventory(root) if any(route["path"].startswith(prefix) for prefix in sensitive)]

def dependency_boundary_inventory(root: Path = ROOT) -> dict[str, list[str]]:
    architecture = architecture_inventory(root)
    boundaries = {}
    for module, info in architecture.items():
        imports = info.get("imports", []) if isinstance(info, dict) else []
        boundaries[module] = sorted({item for item in imports if not ("from ." in item or "import my_ai" in item)})
    return boundaries

def startup_shutdown_inventory(root: Path = ROOT) -> dict[str, Any]:
    api = root / "my_ai" / "api.py"
    text = api.read_text(encoding="utf-8") if api.exists() else ""
    return {
        "lifespan_present": "@asynccontextmanager" in text and "async def lifespan" in text,
        "startup_hooks": sorted(set(re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\(\)", text))),
        "shutdown_hooks": sorted(set(re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\(\)", text))),
    }

def documentation_inventory(root: Path = ROOT) -> dict[str, Any]:
    docs = {}
    for path in sorted((root / "docs").glob("*.md")):
        try:
            source = path.read_text(encoding="utf-8")
            docs[str(path.relative_to(root))] = {
                "lines": len(source.splitlines()),
                "headings": sum(1 for line in source.splitlines() if line.startswith("#")),
                "references_my_ai": "my_ai/" in source or "my_ai." in source,
            }
        except OSError as exc:
            docs[str(path.relative_to(root))] = {"error": str(exc)}
    return docs

def authorization_coverage(root: Path = ROOT) -> list[dict[str, Any]]:
    try:
        from .access_policy import permission_for_path
    except ImportError:
        from my_ai.access_policy import permission_for_path
    findings = []
    for route in route_inventory(root):
        permission = permission_for_path(route["path"], route["method"])
        if permission is None and not route["path"].startswith(("/docs", "/openapi.json", "/redoc", "/static")):
            findings.append({"method": route["method"], "path": route["path"], "status": "unmapped"})
        else:
            findings.append({"method": route["method"], "path": route["path"], "permission": permission, "status": "mapped"})
    return findings

def run_audit(root: Path = ROOT):
    return {
        "silent_failures": find_silent_failures(root),
        "architecture": architecture_inventory(root),
        "configuration": configuration_inventory(root),
        "routes": route_inventory(root),
        "sensitive_routes": sensitive_route_inventory(root),
        "dependency_boundaries": dependency_boundary_inventory(root),
        "startup_shutdown": startup_shutdown_inventory(root),
        "documentation": documentation_inventory(root),
        "authorization": authorization_coverage(root),
    }
