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
    pattern=re.compile(r'os\\.getenv\\(["\']([A-Z][A-Z0-9_]+)["\']')
    for path in sorted((root / 'my_ai').rglob('*.py')):
        try: source=path.read_text(encoding='utf-8')
        except OSError: continue
        for name in sorted(set(pattern.findall(source))): result.append({'path':str(path.relative_to(root)),'environment_variable':name})
    return result

def route_inventory(root: Path = ROOT) -> list[dict[str, str]]:
    result=[]
    pattern=re.compile(r'os\\.getenv\\(["\']([A-Z][A-Z0-9_]+)["\']')
    path=root/'my_ai'/'api.py'
    if path.exists():
        source=path.read_text(encoding='utf-8')
        for method, route in pattern.findall(source): result.append({'method':method.upper(),'path':route})
    return sorted(result,key=lambda x:(x['path'],x['method']))

def run_audit(root: Path = ROOT) -> dict[str, Any]:
    return {"silent_failures":find_silent_failures(root),"architecture":architecture_inventory(root),"configuration":configuration_inventory(root),"routes":route_inventory(root)}
