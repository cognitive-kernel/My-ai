from __future__ import annotations
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from .executor import run_python
from .config import settings


# Toolchain knowledge is data-driven. The runtime does not maintain a language
# allow-list: a semantic planner or a project manifest may describe arbitrary
# executables, commands and installation hints.
DEFAULT_TOOLCHAIN_FILE_NAMES = (
    ".myai/toolchain.json",
    ".myai/toolchains.json",
    "toolchain.json",
    "toolchains.json",
)

# These are generic project-description files, not language mappings. They let
# an unknown/new ecosystem describe its own executable requirements.

def canonical_language(name: str) -> str:
    """Return the semantic label without restricting it to a built-in list."""
    return str(name or "").strip()


def catalog() -> dict[str, Any]:
    return {
        "toolchain_model": {
            "source": "semantic_plan_or_project_descriptor",
            "requirements": ["capabilities", "providers", "executables", "commands", "install"],
            "lifecycle_operations": ["install", "build", "test", "lint", "typecheck", "run"],
        }
    }


def _safe_root(cwd: str | None) -> Path:
    root = Path(os.getenv("MYAI_PROJECT_ROOT", "projects")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = Path(cwd).expanduser().resolve() if cwd else root
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Tool working directory must be inside MYAI_PROJECT_ROOT.")
    if not path.is_dir():
        raise ValueError("Tool working directory does not exist.")
    return path


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _toolchain_descriptors(cwd: Path | None = None) -> list[dict[str, Any]]:
    """Load arbitrary toolchain descriptors without editing Python for new ecosystems."""
    roots = [cwd] if cwd else []
    roots.append(Path(os.getenv("MYAI_PROJECT_ROOT", "projects")).resolve())
    configured = os.getenv("MYAI_TOOLCHAIN_REGISTRY", "").strip()
    paths = [Path(x.strip()) for x in configured.split(os.pathsep) if x.strip()]
    for root in roots:
        if root:
            for name in DEFAULT_TOOLCHAIN_FILE_NAMES:
                paths.append(root / name)
    descriptors: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in paths:
        path = path.expanduser().resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        data = _load_json_file(path)
        items = data.get("toolchains", data.get("requirements", []))
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, list):
            descriptors.extend(x for x in items if isinstance(x, dict))
    return descriptors


def _semantic_requirements(language: str | None, cwd: Path | None = None, planned: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Collect requirements from a semantic descriptor and project metadata.

    No language name is used as a dispatch table. Unknown languages remain
    unknown until their plan/descriptor supplies concrete tool requirements.
    """
    requirements: list[dict[str, Any]] = []
    if planned:
        requirements.extend(item for item in planned if isinstance(item, dict))
    requirements.extend(_toolchain_descriptors(cwd))
    return requirements


def _requirement_executables(requirements: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in requirements:
        providers = item.get("providers", [])
        if isinstance(providers, dict):
            providers = [providers]
        if isinstance(providers, list) and providers:
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                values = provider.get("executables", provider.get("tools", []))
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, list):
                    for value in values:
                        name = str(value).strip()
                        if name and name not in out:
                            out.append(name)
            continue
        values = item.get("executables", item.get("tools", item.get("toolchains", [])))
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            for value in values:
                name = str(value).strip()
                if name and name not in out:
                    out.append(name)
    return out


def _resolve_requirement_providers(requirements: list[dict[str, Any]], auto_install: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []
    for item in requirements:
        providers = item.get("providers", [])
        if isinstance(providers, dict):
            providers = [providers]
        if isinstance(providers, list) and providers:
            selected = None
            candidates: list[dict[str, Any]] = []
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                values = provider.get("executables", provider.get("tools", []))
                if isinstance(values, str):
                    values = [values]
                for executable in values or []:
                    candidate = resolve_tool(str(executable), auto_install=False)
                    candidates.append(candidate)
                    if candidate.get("installed") and selected is None:
                        selected = (provider, candidate)
            if selected is None and auto_install:
                for provider in providers:
                    if not isinstance(provider, dict):
                        continue
                    values = provider.get("executables", provider.get("tools", []))
                    if isinstance(values, str):
                        values = [values]
                    for executable in values or []:
                        candidate = resolve_tool(
                            str(executable),
                            auto_install=True,
                            install=provider.get("install"),
                        )
                        candidates.append(candidate)
                        if candidate.get("installed"):
                            selected = (provider, candidate)
                            break
                    if selected:
                        break
            tools.extend(candidates)
            if selected:
                provider, candidate = selected
                resolved_item = dict(item)
                resolved_item.pop("providers", None)
                resolved_item["executables"] = [candidate["executable"]]
                if provider.get("commands") is not None:
                    resolved_item["commands"] = provider.get("commands")
                if provider.get("install") is not None:
                    resolved_item["install"] = provider.get("install")
                resolved.append(resolved_item)
            continue

        values = item.get("executables", item.get("tools", item.get("toolchains", [])))
        if isinstance(values, str):
            values = [values]
        for executable in values or []:
            install = item.get("install")
            tools.append(resolve_tool(str(executable), auto_install=auto_install, install=install))
        resolved.append(item)
    return resolved, tools


def _commands_for(requirements: list[dict[str, Any]], operation: str) -> list[str]:
    commands: list[str] = []
    for item in requirements:
        value = item.get(operation, item.get("commands", {}).get(operation, []) if isinstance(item.get("commands"), dict) else [])
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            commands.extend(str(x).strip() for x in value if str(x).strip())
    return commands


def _parse_command(command: str) -> list[str]:
    text = str(command or "").strip()
    if not text:
        raise ValueError("Empty semantic command.")
    if any(token in text for token in ("&&", "||", ";", "|", ">", "<")):
        raise ValueError("Shell operators are not allowed in semantic tool commands; use structured lifecycle commands.")
    try:
        return shlex.split(text, posix=os.name != "nt")
    except ValueError as exc:
        raise ValueError(f"Invalid semantic command: {text!r}") from exc



def _windows_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in (
        os.getenv("ProgramFiles"),
        os.getenv("ProgramFiles(x86)"),
        os.getenv("LOCALAPPDATA"),
        os.getenv("ProgramW6432"),
    ):
        if raw:
            path = Path(raw)
            if path.is_dir() and path not in roots:
                roots.append(path)
    return roots


def discover_tool(executable: str) -> str | None:
    """Discover any executable by name; no language-specific registry is required."""
    name = Path(str(executable or "").strip().strip('"')).name
    if not name:
        return None
    env_key = "MYAI_TOOL_" + re.sub(r"[^A-Za-z0-9]+", "_", name).upper()
    configured = os.getenv(env_key, "").strip()
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    found = shutil.which(name)
    if found:
        return str(Path(found).resolve())
    if os.name == "nt":
        for root in _windows_roots():
            try:
                matches = root.rglob(name)
            except OSError:
                continue
            for candidate in matches:
                if candidate.is_file():
                    return str(candidate.resolve())
    return None


def _package_manager() -> str | None:
    for manager in ("winget", "choco", "brew", "apt-get"):
        if shutil.which(manager):
            return manager
    return None


def _install_tool(executable: str, install: Any = None) -> dict[str, Any]:
    """Install only from an explicit trusted descriptor, never from model text."""
    if os.getenv("MYAI_AUTO_INSTALL_TOOLS", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return {"attempted": False, "reason": "automatic installation is disabled"}
    detected_manager = _package_manager()
    spec = install if isinstance(install, dict) else {}
    if not spec:
        return {"attempted": False, "reason": "no trusted installation descriptor is available"}
    manager = str(spec.get("manager") or detected_manager or "").strip().lower()
    if not manager or not shutil.which(manager):
        return {"attempted": False, "reason": f"installation manager is unavailable: {manager or 'none'}"}
    package = spec.get("package")
    if not package:
        package = spec.get("apt" if manager == "apt-get" else manager)
    if not package:
        return {"attempted": False, "reason": f"no package for {manager}"}
    if manager == "winget":
        argv = ["winget", "install", "--id", str(package), "--exact", "--source", "winget",
                "--accept-source-agreements", "--accept-package-agreements", "--disable-interactivity"]
    elif manager == "choco":
        argv = ["choco", "install", str(package), "-y", "--no-progress"]
    elif manager == "brew":
        argv = ["brew", "install", str(package)]
    else:
        argv = ["apt-get", "install", "-y", str(package)]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=900, shell=False)
        return {
            "attempted": True, "manager": manager, "package": package,
            "return_code": p.returncode, "output": (p.stdout + "\n" + p.stderr)[-12000:],
            "passed": p.returncode == 0,
        }
    except Exception as exc:
        return {"attempted": True, "manager": manager, "package": package, "error": str(exc), "passed": False}


def resolve_tool(executable: str, auto_install: bool = True, install: Any = None) -> dict[str, Any]:
    path = discover_tool(executable)
    if path:
        return {"executable": executable, "path": path, "installed": True, "install": None}
    result = _install_tool(executable, install) if auto_install else {
        "attempted": False, "reason": "installation disabled for this operation"
    }
    path = discover_tool(executable) if result.get("passed") else None
    return {"executable": executable, "path": path, "installed": bool(path), "install": result}


def ensure_language_toolchain(
    language: str,
    auto_install: bool = True,
    requirements: list[dict[str, Any]] | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    root = Path(cwd).resolve() if cwd else None
    reqs = requirements if requirements is not None else _semantic_requirements(language, root)
    executables = _requirement_executables(reqs)
    if not executables:
        return {
            "language": canonical_language(language),
            "supported": False,
            "ready": False,
            "tools": [],
            "reason": "No concrete tool requirements were discovered. Provide them in the semantic plan or project descriptor.",
        }
    resolved_requirements, tools = _resolve_requirement_providers(reqs, auto_install)
    return {
        "language": canonical_language(language),
        "supported": True,
        "tools": tools,
        "ready": bool(resolved_requirements) and all(
            item["installed"] for item in tools
            if item["executable"] in _requirement_executables(resolved_requirements)
        ) and all(
            any(
                tool["installed"] and tool["executable"] in item.get("executables", [])
                for tool in tools
            )
            for item in resolved_requirements
        ),
        "requirements": resolved_requirements,
        "planned_requirements": reqs,
    }


def doctor(language: str | None = None, cwd: str | None = None, requirements: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    root = Path(cwd).resolve() if cwd else None
    reqs = requirements if requirements is not None else _semantic_requirements(language, root)
    if language is not None and not reqs:
        return {canonical_language(language): {"status": "no_requirements_discovered"}}
    readiness = ensure_language_toolchain(
        language or "semantic-project",
        auto_install=False,
        requirements=reqs,
        cwd=cwd,
    )
    return {
        readiness["language"]: {
            item["executable"]: item["installed"]
            for item in readiness.get("tools", [])
        }
    }


def _command(
    language: str,
    operation: str,
    requirements: list[dict[str, Any]] | None = None,
    cwd: str | None = None,
) -> list[str]:
    root = Path(cwd).resolve() if cwd else None
    reqs = requirements if requirements is not None else _semantic_requirements(language, root)
    commands = _commands_for(reqs, operation)
    if not commands:
        raise ValueError(
            f"No semantic command for operation {operation!r}. "
            "Declare it in the semantic plan or project toolchain descriptor."
        )
    for text in commands:
        argv = _parse_command(text)
        exe = argv[0]
        resolved = discover_tool(exe)
        if resolved:
            return [resolved, *argv[1:]]
    first = _parse_command(commands[0])[0]
    raise RuntimeError(f"Required executable was not found: {first}")


def run_project_tool(
    language: str,
    operation: str,
    cwd: str | None = None,
    timeout: int = 120,
    requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    path = _safe_root(cwd)
    readiness = ensure_language_toolchain(
        language,
        auto_install=True,
        requirements=requirements,
        cwd=str(path),
    )
    if not readiness.get("ready"):
        missing = [x.get("executable") for x in readiness.get("tools", []) if not x.get("installed")]
        raise RuntimeError(
            f"Required toolchain is unavailable for {canonical_language(language)}: "
            + (", ".join(missing) if missing else readiness.get("reason", "unknown reason"))
        )
    reqs = readiness.get("requirements", [])
    argv = _command(language, operation, requirements=reqs, cwd=str(path))
    argv = [part.replace("{PROJECT_ROOT}", str(path)) for part in argv]
    timeout = max(1, min(int(timeout), 600))
    try:
        p = subprocess.run(
            argv, cwd=path, capture_output=True, text=True, timeout=timeout, shell=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
        return {
            "language": canonical_language(language), "operation": operation, "command": argv,
            "cwd": str(path), "return_code": p.returncode, "output": p.stdout[-12000:],
            "error": p.stderr[-12000:], "passed": p.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "language": canonical_language(language), "operation": operation, "command": argv,
            "cwd": str(path), "return_code": -1, "output": "",
            "error": "Tool execution timed out.", "passed": False,
        }


def run_python_snippet(code:str):
    result=run_python(code)
    return {"output":result.output,"error":result.error,"return_code":result.return_code,"timed_out":result.timed_out,"sandbox_mode":result.sandbox_mode}

_READONLY_BLOCK=re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC(?:UTE)?|BACKUP|RESTORE)\b",re.I)

def _validate_readonly_sql(sql:str)->str:
    text=str(sql or "").strip()
    if not text: raise ValueError("SQL query is required.")
    if len(text)>20000: raise ValueError("SQL query is too long.")
    if ";" in text.rstrip(";"): raise ValueError("Only one SQL statement is allowed.")
    if _READONLY_BLOCK.search(text): raise ValueError("Only read-only SQL is permitted.")
    if not re.match(r"^(SELECT|WITH)\b",text,re.I): raise ValueError("Only SELECT/WITH queries are permitted.")
    return text

def _sqlserver_connection():
    conn_string=os.getenv("MYAI_SQLSERVER_CONNECTION_STRING","").strip()
    if not conn_string: raise RuntimeError("MYAI_SQLSERVER_CONNECTION_STRING is not configured.")
    try:
        import mssql_python
    except ImportError:
        try:
            import pyodbc as mssql_python
        except ImportError as exc:
            raise RuntimeError("Install mssql-python (preferred) or pyodbc to enable SQL Server tools.") from exc
    return mssql_python.connect(conn_string, autocommit=False)

def sqlserver_query(sql:str,limit:int=1000)->dict[str,Any]:
    query=_validate_readonly_sql(sql)
    conn=_sqlserver_connection()
    try:
        cur=conn.cursor()
        cur.execute(query)
        columns=[str(x[0]) for x in cur.description or []]
        rows=[]
        for row in cur.fetchmany(max(1,min(int(limit),5000))):
            rows.append({columns[i]:row[i] for i in range(len(columns))})
        return {"columns":columns,"rows":rows,"row_count":len(rows),"truncated":len(rows)>=max(1,min(int(limit),5000))}
    finally:
        conn.close()

def sqlserver_schema(limit:int=500)->dict[str,Any]:
    return sqlserver_query("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATA_TYPE,ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION",limit)

def _safe_sqlite_path(value: str) -> Path:
    db=Path(value).expanduser().resolve()
    primary=Path(settings.db_path).expanduser().resolve()
    root=Path(os.getenv("MYAI_SQLITE_ROOT","data/sqlite")).expanduser().resolve()
    if db != primary:
        try:
            db.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"SQLite paths must be the active database or stay under {root}.") from exc
    return db

def sqlite_schema(path:str)->dict[str,Any]:
    db=_safe_sqlite_path(path)
    if not db.is_file(): raise ValueError("SQLite database file not found.")
    conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    try:
        rows=conn.execute("SELECT name,type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name").fetchall()
        return {"rows":[{"name":r[0],"type":r[1]} for r in rows]}
    finally: conn.close()

def _mysql_connection():
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError("Install mysql-connector-python to enable MySQL tools.") from exc
    cfg=os.getenv("MYAI_MYSQL_CONFIG","").strip()
    if not cfg:
        raise RuntimeError("MYAI_MYSQL_CONFIG must contain a JSON connection object.")
    import json
    return mysql.connector.connect(**json.loads(cfg))

def mysql_query(sql:str,limit:int=1000)->dict[str,Any]:
    query=_validate_readonly_sql(sql)
    conn=_mysql_connection()
    try:
        cur=conn.cursor()
        cur.execute(query)
        columns=[str(x[0]) for x in cur.description or []]
        rows=[dict(zip(columns,row)) for row in cur.fetchmany(max(1,min(int(limit),5000)))]
        return {"columns":columns,"rows":rows,"row_count":len(rows)}
    finally: conn.close()

def mysql_schema(limit:int=500)->dict[str,Any]:
    return mysql_query("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATA_TYPE,ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION",limit)

def sqlite_query(path:str,sql:str,limit:int=1000)->dict[str,Any]:
    query=_validate_readonly_sql(sql)
    db=_safe_sqlite_path(path)
    conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    try:
        cur=conn.execute(query)
        columns=[d[0] for d in cur.description or []]
        rows=[dict(zip(columns,row)) for row in cur.fetchmany(max(1,min(int(limit),5000)))]
        return {"columns":columns,"rows":rows,"row_count":len(rows)}
    finally: conn.close()
