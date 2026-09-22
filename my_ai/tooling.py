from __future__ import annotations
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from .executor import run_python

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
}

ALIASES={"js":"JavaScript","node":"JavaScript","py":"Python","kotlin":"Kotlin","kt":"Kotlin","swift":"Swift","rust":"Rust","rs":"Rust","c":"C","php":"PHP","android":"Android","ios":"iOS"}

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

def doctor(language:str|None=None)->dict[str,Any]:
    names=[canonical_language(language)] if language else list(LANGUAGE_TOOLS)
    out={}
    for name in names:
        spec=LANGUAGE_TOOLS.get(name)
        if not spec: raise ValueError(f"Unsupported language: {language}")
        out[name]={tool:bool(shutil.which(tool)) for tool in spec["toolchains"]}
    return out

def _command(language:str,operation:str)->list[str]:
    lang=canonical_language(language)
    spec=LANGUAGE_TOOLS.get(lang)
    if not spec: raise ValueError(f"Unsupported language: {language}")
    commands=spec.get(operation,[])
    if not commands: raise ValueError(f"Operation {operation} is not defined for {lang}.")
    for text in commands:
        exe=text.split()[0]
        if shutil.which(exe) or exe in {"vendor/bin/phpunit","gradle","npm","swift","xcodebuild"}:
            return text.split()
    return commands[0].split()

def run_project_tool(language:str,operation:str,cwd:str|None=None,timeout:int=120)->dict[str,Any]:
    path=_safe_root(cwd)
    argv=_command(language,operation)
    exe=argv[0]
    if os.sep in exe or "/" in exe:
        candidate=path/exe
        if not candidate.exists(): raise RuntimeError(f"Required project tool was not found: {exe}")
    elif not shutil.which(exe):
        raise RuntimeError(f"Required toolchain executable was not found: {exe}")
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

def sqlite_schema(path:str)->dict[str,Any]:
    db=Path(path).expanduser().resolve()
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
    finally:
        conn.close()

def mysql_schema(limit:int=500)->dict[str,Any]:
    return mysql_query("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATA_TYPE,ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION",limit)

def sqlite_query(path:str,sql:str,limit:int=1000)->dict[str,Any]:
    query=_validate_readonly_sql(sql)
    db=Path(path).expanduser().resolve()
    conn=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    try:
        cur=conn.execute(query)
        columns=[d[0] for d in cur.description or []]
        rows=[dict(zip(columns,row)) for row in cur.fetchmany(max(1,min(int(limit),5000)))]
        return {"columns":columns,"rows":rows,"row_count":len(rows)}
    finally: conn.close()
