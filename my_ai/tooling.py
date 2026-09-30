from __future__ import annotations
import json
import os
import re
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
PROJECT_DESCRIPTORS = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "build.gradle",
    "build.gradle.kts",
    "pom.xml",
    "Makefile",
    "CMakeLists.txt",
    "Package.swift",
    "*.csproj",
    "*.sln",
    "*.mq4",
    "*.mqh",
    "AndroidManifest.xml",
)


def canonical_language(name: str) -> str:
    """Return the semantic label without restricting it to a built-in list."""
    return str(name or "").strip()


def catalog() -> dict[str, Any]:
    return {
        "toolchain_model": {
            "source": "semantic_plan_or_project_descriptor",
            "requirements": ["executable", "version", "capabilities", "commands", "install"],
        },
        "databases": {
            "SQL Server": ["schema", "tables", "columns", "readonly_query"],
            "MySQL": ["schema", "tables", "columns", "readonly_query"],
            "SQLite": ["schema", "tables", "readonly_query"],
        },
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


def _project_files(cwd: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in PROJECT_DESCRIPTORS:
        try:
            files.extend(cwd.glob(pattern))
        except OSError:
            pass
    return list(dict.fromkeys(p for p in files if p.is_file()))


def _semantic_requirements(language: str | None, cwd: Path | None = None) -> list[dict[str, Any]]:
    """Collect requirements from a semantic descriptor and project metadata.

    No language name is used as a dispatch table. Unknown languages remain
    unknown until their plan/descriptor supplies concrete tool requirements.
    """
    requirements: list[dict[str, Any]] = []
    requirements.extend(_toolchain_descriptors(cwd))
    if cwd:
        # A generated project can declare its own executable/command contract.
        for path in _project_files(cwd):
            if path.name in {"toolchain.json", "toolchains.json"}:
                continue
            if path.suffix == ".mq4" or path.suffix == ".mqh":
                requirements.append({"capabilities": ["mql4"], "executables": ["metaeditor.exe"]})
            elif path.name == "package.json":
                requirements.append({"capabilities": ["javascript"], "executables": ["node", "npm"]})
            elif path.name in {"pyproject.toml"}:
                requirements.append({"capabilities": ["python"], "executables": ["python"]})
            elif path.name == "Cargo.toml":
                requirements.append({"capabilities": ["rust"], "executables": ["cargo", "rustc"]})
            elif path.name in {"build.gradle", "build.gradle.kts", "AndroidManifest.xml"}:
                requirements.append({"capabilities": ["gradle"], "executables": ["java", "gradle"]})
    return requirements


def _requirement_executables(requirements: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in requirements:
        values = item.get("executables", item.get("tools", item.get("toolchains", [])))
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            for value in values:
                name = str(value).strip()
                if name and name not in out:
                    out.append(name)
    return out


def _commands_for(requirements: list[dict[str, Any]], operation: str) -> list[str]:
    commands: list[str] = []
    for item in requirements:
        value = item.get(operation, item.get("commands", {}).get(operation, []) if isinstance(item.get("commands"), dict) else [])
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            commands.extend(str(x).strip() for x in value if str(x).strip())
    return commands


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
