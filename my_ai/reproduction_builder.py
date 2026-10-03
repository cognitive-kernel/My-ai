from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_workspace(spec: dict[str, Any], root: str | Path) -> dict[str, Any]:
    workspace = Path(root).expanduser().resolve()
    (workspace / "frontend").mkdir(parents=True, exist_ok=True)
    (workspace / "backend").mkdir(parents=True, exist_ok=True)
    (workspace / "tests").mkdir(parents=True, exist_ok=True)

    routes = list(spec.get("requirements", {}).get("navigation_links", []))
    forms = list(spec.get("requirements", {}).get("forms", []))
    title = str(spec.get("ui", {}).get("title") or "Reproduced Project")
    _write(workspace / "README.md", f"""# {title}

Generated from an authorized source specification.

This workspace is an independent implementation. Secrets, cookies, tokens and private credentials are never copied.
""")
    _write(workspace / "reproduction.spec.json", json.dumps(spec, ensure_ascii=False, indent=2))
    _write(workspace / "frontend" / "routes.json", json.dumps({"routes": routes}, ensure_ascii=False, indent=2))
    _write(workspace / "frontend" / "index.html", f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>body{{font-family:system-ui;margin:0;padding:2rem;max-width:1100px;margin-inline:auto}}nav a{{margin:.35rem}}form{{padding:1rem;border:1px solid #ddd;border-radius:.75rem;margin:1rem 0}}label{{display:block;margin:.5rem 0}}input,select,textarea{{width:100%;box-sizing:border-box;padding:.55rem}}</style></head>
<body><h1>{title}</h1><nav id="nav"></nav><main id="app"><p>Independent reconstruction generated from the specification.</p></main>
<script>
const routes={json.dumps(routes, ensure_ascii=False)};
const forms={json.dumps(forms, ensure_ascii=False)};
document.getElementById("nav").innerHTML=routes.map(u=>'<a href="'+u+'">'+u+'</a>').join("");
document.getElementById("app").insertAdjacentHTML("beforeend", forms.map(f=>'<form><strong>'+String(f.method||"GET")+' '+String(f.action||"")+'</strong>'+
(f.fields||[]).map(x=>'<label>'+String(x.name||x.type||"field")+'<input name="'+String(x.name||"")+'" type="'+String(x.type||"text")+'"'+(x.required?' required':'')+'></label>').join("")+
'<button type="submit">Submit</button></form>').join(""));
</script></body></html>
""")
    _write(workspace / "backend" / "app.py", """from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Independent Reproduction")
ROOT = Path(__file__).resolve().parents[1]

@app.get("/health")
def health():
    return {"status": "ok", "independent": True}

@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")
""")
    _write(workspace / "backend" / "requirements.txt", "fastapi>=0.115\nuvicorn>=0.30\n")
    _write(workspace / "tests" / "test_health.py", """from fastapi.testclient import TestClient
from backend.app import app

def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"
""")
    return {
        "workspace": str(workspace),
        "files": [
            "README.md", "reproduction.spec.json", "frontend/routes.json",
            "frontend/index.html", "backend/app.py", "backend/requirements.txt",
            "tests/test_health.py",
        ],
        "independent": True,
        "secrets_copied": False,
        "generated_components": len(forms),
        "generated_routes": len(routes),
    }


def compare_spec_to_workspace(spec: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve()
    expected = [
        root / "README.md", root / "reproduction.spec.json", root / "frontend" / "routes.json",
        root / "frontend" / "index.html", root / "backend" / "app.py",
        root / "backend" / "requirements.txt", root / "tests" / "test_health.py",
    ]
    missing = [str(path.relative_to(root)) for path in expected if not path.exists()]
    expected_routes = set(spec.get("requirements", {}).get("navigation_links", []))
    actual_routes = set(json.loads((root / "frontend" / "routes.json").read_text(encoding="utf-8")).get("routes", [])) if (root / "frontend" / "routes.json").exists() else set()
    return {
        "passed": not missing and expected_routes.issubset(actual_routes),
        "missing": missing,
        "workspace": str(root),
        "route_coverage": len(expected_routes & actual_routes) / len(expected_routes) if expected_routes else 1.0,
        "coverage": 1.0 if not missing else 1.0 - len(missing) / len(expected),
    }
