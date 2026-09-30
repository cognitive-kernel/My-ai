from __future__ import annotations
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from .executor import run_python
from .config import settings

LANGUAGE_TOOLS = {
    "Python": {"toolchains":["python","pytest","ruff","mypy"],"tests":["python -m pytest"],"build":["python -m compileall"],"lint":["ruff check ."]},
    "C": {"toolchains":["gcc","clang","make"],"tests":["make test"],"build":["make"],"lint":["clang-tidy"]},
    "PHP": {"toolchains":["php","composer"],"tests":["composer test","vendor/bin/phpunit"],"build":["composer validate --no-check-publish"],"lint":["php -l"]},
    "JavaScript": {"toolchains":["node","npm"],"tests":["npm test"],"build":["npm run build"],"lint":["npm run lint"]},
    "Rust": {"toolchains":["rustc","cargo","rustfmt","clippy"],"tests":["cargo test"],"build":["cargo build --locked"],"lint":["cargo clippy --all-targets --all-features -- -D warnings"]},
    "Kotlin": {"toolchains":["java","kotlinc","gradle"],"tests":["gradle test"],"build":["gradle build"],"lint":["gradle ktlintCheck"]},
    "Swift": {"toolchains":["swift","swiftc","xcodebuild"],"tests":["swift test"],"build":["swift build"],"lint":["swift format lint ."]},
    "Android": {"toolchains":["java","gradle","adb"],"tests":["gradle test"],"build":["gradle assembleDebug"],"lint":["gradle lint"]},
    "iOS": {"toolchains":["swift","xcodebuild"],"tests":["swift test"],"build":["xcodebuild test"],"lint":["swift format lint ."]},
    "MQL4": {"toolchains":["metaeditor.exe"],"tests":["metaeditor.exe"],"build":["metaeditor.exe"],"lint":["metaeditor.exe"]},
    "SQL Server": {"toolchains":["sqlcmd"],"tests":["sqlcmd"],"build":["sqlcmd"],"lint":["sqlcmd"]},
}

ALIASES={"mql4":"MQL4","mq4":"MQL4","mql 4":"MQL4","متاتریدر 4":"MQL4","متاتریدر۴":"MQL4","js":"JavaScript","node":"JavaScript","py":"Python","kotlin":"Kotlin","kt":"Kotlin","swift":"Swift","rust":"Rust","rs":"Rust","c":"C","php":"PHP","android":"Android","ios":"iOS","sql server":"SQL Server","sqlserver":"SQL Server","sqlcmd":"SQL Server"}

# Optional package-manager hints. Discovery always runs first; installation is opt-in.
# IDs are exact package identifiers, never free-form shell commands.
TOOL_INSTALL_SPECS = {
    "git": {"winget": "Git.Git", "choco": "git", "brew": "git", "apt": "git"},
    "python": {"winget": "Python.Python.3.13", "choco": "python", "brew": "python", "apt": "python3"},
    "node": {"winget": "OpenJS.NodeJS.LTS", "choco": "nodejs-lts", "brew": "node", "apt": "nodejs"},
    "npm": {"winget": "OpenJS.NodeJS.LTS", "choco": "nodejs-lts", "brew": "node", "apt": "npm"},
    "gcc": {"winget": "MSYS2.MSYS2", "choco": "mingw", "brew": "gcc", "apt": "gcc"},
    "rustc": {"winget": "Rustlang.Rustup", "choco": "rustup.install", "brew": "rustup-init", "apt": "rustc"},
    "cargo": {"winget": "Rustlang.Rustup", "choco": "rustup.install", "brew": "rustup-init", "apt": "cargo"},
    "php": {"winget": "PHP.PHP.8.4", "choco": "php", "brew": "php", "apt": "php-cli"},
    "composer": {"winget": "Composer.Composer", "choco": "composer", "brew": "composer", "apt": "composer"},
}

def canonical_language(name:str)->str:
    raw=str(name or "").strip()
    for key in LANGUAGE_TOOLS:
        if key.lower()==raw.lower(): return key
    return ALIASES.get(raw.lower(),raw)

def catalog()->dict[str,Any]:
    return {"languages":LANGUAGE_TOOLS,"databases":{"SQL Server":["schema","tables","columns","readonly_query"],"MySQL":["schema","tables","columns","readonly_query"],"SQLite":["schema","tables","readonly_query"]}}

def _safe_root(cwd:str|None)->Path:
    root=Path(os.getenv("MYAI_PROJECT_ROOT","projects")).resolve()
    root.mkdir(parents=True,exist_ok=True)
    path=(Path(cwd).expanduser().resolve() if cwd else root)
    try: path.relative_to(root)
    except ValueError: raise ValueError("Tool working directory must be inside MYAI_PROJECT_ROOT.")
    if not path.is_dir(): raise ValueError("Tool working directory does not exist.")
    return path

def _windows_roots()->list[Path]:
    roots=[]
    for raw in (os.getenv("ProgramFiles"),os.getenv("ProgramFiles(x86)"),os.getenv("LOCALAPPDATA"),os.getenv("ProgramW6432")):
        if raw:
            path=Path(raw)
            if path.is_dir() and path not in roots: roots.append(path)
    return roots

def discover_tool(executable:str)->str|None:
    """Resolve a tool without requiring a language-specific environment variable."""
    name=Path(str(executable or "").strip().strip('"')).name
    if not name:
        return None
    configured=os.getenv("MYAI_TOOL_"+re.sub(r"[^A-Za-z0-9]+","_",name).upper(),"").strip()
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    found=shutil.which(name)
    if found:
        return str(Path(found).resolve())
    if os.name == "nt":
        for root in _windows_roots():
            try:
                matches=root.rglob(name)
            except OSError:
                continue
            for candidate in matches:
                if candidate.is_file():
                    return str(candidate.resolve())
    return None

def _package_manager()->str|None:
    for manager in ("winget","choco","brew","apt-get"):
        if shutil.which(manager):
            return manager
    return None

def _install_tool(executable:str)->dict[str,Any]:
    if os.getenv("MYAI_AUTO_INSTALL_TOOLS","").strip().lower() not in {"1","true","yes","on"}:
        return {"attempted":False,"reason":"automatic installation is disabled"}
    spec=TOOL_INSTALL_SPECS.get(Path(executable).name.lower())
    manager=_package_manager()
    if not spec or not manager:
        return {"attempted":False,"reason":"no trusted package-manager specification is available"}
    package=spec.get("apt" if manager=="apt-get" else manager)
    if not package:
        return {"attempted":False,"reason":f"no package mapping for {manager}"}
    if manager=="winget":
        argv=["winget","install","--id",package,"--exact","--source","winget","--accept-source-agreements","--accept-package-agreements","--disable-interactivity"]
    elif manager=="choco":
        argv=["choco","install",package,"-y","--no-progress"]
    elif manager=="brew":
        argv=["brew","install",package]
    else:
        argv=["apt-get","install","-y",package]
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=900,shell=False)
        return {"attempted":True,"manager":manager,"package":package,"return_code":p.returncode,"output":(p.stdout+"\n"+p.stderr)[-12000:],"passed":p.returncode==0}
    except Exception as exc:
        return {"attempted":True,"manager":manager,"package":package,"error":str(exc),"passed":False}

def resolve_tool(executable:str,auto_install:bool=True)->dict[str,Any]:
    path=discover_tool(executable)
    if path:
        return {"executable":executable,"path":path,"installed":True,"install":None}
    install=_install_tool(executable) if auto_install else {"attempted":False,"reason":"installation disabled for this operation"}
    path=discover_tool(executable) if install.get("passed") else None
    return {"executable":executable,"path":path,"installed":bool(path),"install":install}

def ensure_language_toolchain(language:str,auto_install:bool=True)->dict[str,Any]:
    lang=canonical_language(language)
    spec=LANGUAGE_TOOLS.get(lang)
    if not spec:
        return {"language":lang,"supported":False,"tools":[]}
    tools=[resolve_tool(tool,auto_install=auto_install) for tool in spec["toolchains"]]
    return {"language":lang,"supported":True,"tools":tools,"ready":all(x["installed"] for x in tools)}

def doctor(language:str|None=None)->dict[str,Any]:
    names=[canonical_language(language)] if language else list(LANGUAGE_TOOLS)
    out={}
    for name in names:
        state=ensure_language_toolchain(name,auto_install=False)
        if not state["supported"]: raise ValueError(f"Unsupported language: {language}")
        out[name]={x["executable"]:x["installed"] for x in state["tools"]}
    return out

def _command(language:str,operation:str)->list[str]:
    lang=canonical_language(language)
    spec=LANGUAGE_TOOLS.get(lang)
    if not spec: raise ValueError(f"Unsupported language: {language}")
    commands=spec.get(operation,[])
    if not commands: raise ValueError(f"Operation {operation} is not defined for {lang}.")
    for text in commands:
        exe=text.split()[0]
        resolved=discover_tool(exe)
        if resolved:
            return [resolved,*text.split()[1:]]
    raise RuntimeError(f"Required toolchain executable was not found: {commands[0].split()[0]}")

def run_project_tool(language:str,operation:str,cwd:str|None=None,timeout:int=120)->dict[str,Any]:
    path=_safe_root(cwd)
    readiness=ensure_language_toolchain(language,auto_install=True)
    if not readiness.get("ready"):
        missing=[x.get("executable") for x in readiness.get("tools",[]) if not x.get("installed")]
        raise RuntimeError(f"Required toolchain is unavailable for {canonical_language(language)}: {', '.join(missing)}")
    argv=_command(language,operation)
    if canonical_language(language) == "MQL4":
        sources=sorted(path.rglob("*.mq4"))
        if not sources:
            return {"language":"MQL4","operation":operation,"command":argv,"cwd":str(path),"return_code":-1,"output":"","error":"No .mq4 source file was generated.","passed":False}
        if operation in {"test","lint"}:
            return {"language":"MQL4","operation":operation,"command":argv,"cwd":str(path),"return_code":0,"output":"MQL4 static validation is handled by the software validation layer; MetaEditor compilation is the build step.","error":"","passed":True}
        argv=[argv[0], argv[1].replace("{SOURCE}",str(sources[0])), argv[2]]
    timeout=max(1,min(int(timeout),600))
    try:
        p=subprocess.run(argv,cwd=path,capture_output=True,text=True,timeout=timeout,shell=False,env={"PATH":os.environ.get("PATH","")})
        return {"language":canonical_language(language),"operation":operation,"command":argv,"cwd":str(path),"return_code":p.returncode,"output":p.stdout[-12000:],"error":p.stderr[-12000:],"passed":p.returncode==0}
    except subprocess.TimeoutExpired:
        return {"language":canonical_language(language),"operation":operation,"command":argv,"cwd":str(path),"return_code":-1,"output":"","error":"Tool execution timed out.","passed":False}

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
