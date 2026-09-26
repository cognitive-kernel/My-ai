from __future__ import annotations
from contextlib import asynccontextmanager
import os
import sys
import subprocess
import re
from urllib.parse import urlparse
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,HttpUrl,Field
from .agent import Agent
from .command_policy import parse_command
from .config import settings
from .settings_store import get_bool, get_int, get_github_settings
from .curriculum import canonical_language,LANGUAGE_CURRICULA
from .db import fetch_all,init_db,execute
from .learner import LearningEngine
from .dynamic_learning import resolve_learning_target
from .router import classify
from .scheduler import StudyScheduler
from .ui import page
from .feature_routes import register_routes
from .learning_resilience import install as install_learning_resilience
from .ui_extensions import install_ui_extensions
from .help import page as help_page, ask_help, local_help_html, apply_help_update
from .git_connector import GitHubConnector
from .auth import authenticate, audit, create_account, create_session, current_user, require_admin, revoke_session, require_user, tool_allowed, TOOL_RULES as AUTH_TOOL_RULES, PATH_ACTIONS as AUTH_PATH_ACTIONS
from .platform import backup_database, choose_model, eval_retrieval, export_database, hybrid_search, import_database, model_health, resource_status, voice_status, web_fetch_policy
from .self_update import status as self_update_status, apply_confirmed_update as self_update_apply, preview_update
from .self_repair import diagnose_local, propose_repair, apply_repair, proposal_status
from .skill_engine import ensure_skill, record_evidence, revalidate, snapshot, record_review, review_snapshot
from .voice import status as voice_engine_status, transcribe, synthesize
from .metrics import snapshot as metrics_snapshot
from .platform import import_encrypted_database, restore_encrypted_backup
from .self_repair import list_proposals, proposal_diff
from .self_diagnostics import SelfDiagnosticsMonitor, latest_report, report_history
from .tooling import catalog as tool_catalog, doctor as tool_doctor, run_project_tool, run_python_snippet, sqlserver_query, sqlserver_schema, mysql_query, mysql_schema, sqlite_query, sqlite_schema
from .image_generation import generate_image, ImageGenerationError
from .runtime_prerequisites import startup_check, runtime_status
from .readiness import build_readiness

scheduler=StudyScheduler()
self_diagnostics=SelfDiagnosticsMonitor()
@asynccontextmanager
async def lifespan(_):
    init_db()
    # Re-check on every application start; installation is limited to the explicit prerequisite manager.
    startup_check()
    under_pytest = (
        os.environ.get("PYTEST_CURRENT_TEST") is not None
        or any("pytest" in str(arg).lower() for arg in sys.argv)
    )
    if not under_pytest:
        self_diagnostics.start()
        scheduler.start_learning_supervisor()
        scheduler.start_review_monitor()
        workers=fetch_all("SELECT language,session_id,status FROM learning_workers WHERE status IN ('running','retrying','paused','stopping')")
        if workers:
            for worker in workers:
                scheduler.start(worker["language"], worker["session_id"])
        else:
            runtime=fetch_all("SELECT language,session_id,status FROM learning_runtime WHERE id=1")
            if runtime and runtime[0]["status"] in {"running","stopping","retrying","paused"} and runtime[0]["language"]:
                scheduler.start(runtime[0]["language"], runtime[0]["session_id"])
    yield
    if not under_pytest:
        scheduler.stop()
        self_diagnostics.stop()
app=FastAPI(title="My-AI",version="0.2.0",description="Local-first personal learning and coding agent.",lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")

register_routes(app, scheduler, require_user, audit)
install_learning_resilience()
install_ui_extensions(app)

_PUBLIC_PATHS = {"/", "/login", "/register", "/auth/register", "/auth/login", "/auth/logout", "/auth/register/status", "/health", "/health/metrics", "/openapi.json", "/docs", "/redoc"}
_TOOL_RULES = AUTH_TOOL_RULES
_PATH_ACTIONS = AUTH_PATH_ACTIONS
_LOGIN_FAILURES: dict[str, tuple[int, float]] = {}
_LOGIN_FAILURE_LIMIT = 5
_LOGIN_FAILURE_WINDOW = 300.0

def _login_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{username.strip().lower()}"

def _cleanup_login_failures(now: float) -> None:
    stale = [k for k, (_, started) in _LOGIN_FAILURES.items() if now - started > _LOGIN_FAILURE_WINDOW]
    for key in stale:
        _LOGIN_FAILURES.pop(key, None)
    if len(_LOGIN_FAILURES) > 10000:
        for key in list(_LOGIN_FAILURES)[:5000]:
            _LOGIN_FAILURES.pop(key, None)


@app.middleware("http")
async def auth_and_audit_middleware(request: Request, call_next):
    path=request.url.path
    user=current_user(request)
    if path not in _PUBLIC_PATHS and not path.startswith("/docs/") and not user:
        if "application/json" in request.headers.get("accept","").lower():
            return JSONResponse({"detail":"Authentication required."},status_code=401)
        return RedirectResponse("/login",status_code=303)
    if settings.read_only and request.method in {"POST", "PUT", "PATCH", "DELETE"} and path not in {"/auth/login", "/auth/logout"} and not path.startswith("/docs/"):
        return JSONResponse({"detail":"MYAI_READ_ONLY is enabled; write operation blocked."}, status_code=423)
    if user and user["role"] != "admin":
        permission = None
        for prefix,tool in _TOOL_RULES:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                action=_PATH_ACTIONS.get(path, "read" if request.method=="GET" else "write" if request.method in {"PUT","PATCH","DELETE"} else "execute")
                permission = (tool, action)
                break
        if permission is None:
            # Legacy routes without an explicit tool mapping are read-only for
            # ordinary users. New write/execute routes must opt into a rule.
            if request.method != "GET" and path not in {"/auth/login", "/auth/logout", "/auth/register", "/auth/register/status"}:
                return JSONResponse({"detail":"Tool permission denied: unmapped write/execute route."}, status_code=403)
        else:
            tool, action = permission
            if not tool_allowed(user,tool,action):
                return JSONResponse({"detail":f"Tool permission denied: {tool}:{action}"},status_code=403)
    response=await call_next(request)
    if user and path!="/auth/logout":
        action={"GET":"read","POST":"execute","PUT":"write","PATCH":"write","DELETE":"write"}.get(request.method,request.method.lower())
        audit(user,path,action,str(response.status_code))
    return response

agent=Agent(); learner=LearningEngine()
VOICE_ROOT=Path("data/voice").resolve()
def _voice_path(value:str, must_exist:bool=False) -> str:
    path=Path(value).expanduser().resolve()
    try: path.relative_to(VOICE_ROOT)
    except ValueError: raise HTTPException(400,"Voice paths must stay under data/voice.")
    if must_exist and not path.is_file(): raise HTTPException(404,"Voice input/model file not found.")
    return str(path)
class ChatRequest(BaseModel): message:str; session_id:int|None=None
class SelfUpdateRequest(BaseModel): health_url: HttpUrl | None = None
class RepairRequest(BaseModel): issue:str=""; proposal_id:str|None=None; approved:bool=False
class AuthRegisterRequest(BaseModel): username:str; password:str; display_name:str=""
class AuthLoginRequest(BaseModel): username:str; password:str
class KnowledgeUpdateRequest(BaseModel): title:str; content:str; topic:str; source_url:str|None=None
class BackupRequest(BaseModel): path:str; password:str|None=None
class ImportRequest(BaseModel): path:str; password:str|None=None; destination:str|None=None
class PermissionRequest(BaseModel): user_id:int; tool_name:str; action:str; allowed:bool
class AdminUserRequest(BaseModel): username:str; password:str; display_name:str=""; active:bool=True
class SkillEvidenceRequest(BaseModel): skill_id:int; kind:str; passed:bool; details:dict[str,object]={}
class SkillRevalidateRequest(BaseModel): skill_id:int; version:str
class VoiceTranscribeRequest(BaseModel): audio_path:str; model_path:str; language:str="fa"
class VoiceSynthesizeRequest(BaseModel): text:str; model_path:str; output_path:str
class URLRequest(BaseModel): url:HttpUrl; topic:str="Python"
class ProjectRequest(BaseModel): goal:str
class CodeRequest(BaseModel): code:str; confirmed:bool=False
class ProgramRequest(BaseModel): request:str; language:str="Python"
class LanguageRequest(BaseModel): language:str="Python"
class SecurityRequest(BaseModel): project_path:str|None=None; target_url:str|None=None; code:str|None=None; language:str="Python"; fix:bool=False; headers:dict[str,str]=Field(default_factory=dict)
class GitRequest(BaseModel): repository:str; path:str|None=None; ref:str|None=None; branch:str|None=None; content:str|None=None; message:str|None=None; allow_write:bool=False
class SchedulerRequest(BaseModel): language:str="Python"; interval_seconds:int=settings.scheduler_interval_seconds
class LearnRequest(BaseModel): language:str="Python"; interval_seconds:int=settings.scheduler_interval_seconds
class ToolRequest(BaseModel): language:str="Python"; operation:str="test"; cwd:str|None=None; timeout:int=120; confirmed:bool=False
class PythonToolRequest(BaseModel): code:str; confirmed:bool=False
class SQLQueryRequest(BaseModel): sql:str; limit:int=1000
class SQLiteQueryRequest(BaseModel): path:str; sql:str; limit:int=1000

@app.get("/",response_class=HTMLResponse)
def home(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(
        page(),
        headers={
            "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
            "Pragma":"no-cache",
            "Expires":"0",
        },
    )

LOGIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ورود | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.box{max-width:420px;margin:10vh auto;background:#fff;padding:28px;border-radius:16px}input,button{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:9px;border:1px solid #ccc}button{cursor:pointer;background:#111827;color:#fff}.err{color:#b91c1c}</style><div class='box'><h1>ورود به My-AI</h1><input id='u' placeholder='نام کاربری'><input id='p' type='password' placeholder='رمز عبور'><button onclick='login()'>ورود</button><p id='e' class='err'></p><a id='register-link' href='/register'>ساخت اولین حساب</a></div><script>fetch('/auth/register/status').then(r=>r.json()).then(x=>{if(x.open===false)document.getElementById('register-link').remove()}).catch(()=>{});async function login(){e.textContent='';let r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let j=await r.json();if(!r.ok){e.textContent=j.detail||'خطا';return}location.href='/'}</script>"""
REGISTER_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ساخت حساب | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.box{max-width:420px;margin:10vh auto;background:#fff;padding:28px;border-radius:16px}input,button{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:9px;border:1px solid #ccc}button{cursor:pointer;background:#111827;color:#fff}.err{color:#b91c1c}.note{background:#ecfdf5;padding:10px;border-radius:8px}</style><div class='box'><h1>ساخت حساب My-AI</h1><p class='note'>اگر هنوز هیچ حسابی ساخته نشده باشد، این حساب به‌صورت خودکار <b>ادمین اصلی</b> می‌شود و به همه ابزارها دسترسی خواهد داشت.</p><input id='n' placeholder='نام نمایشی'><input id='u' placeholder='نام کاربری'><input id='p' type='password' placeholder='رمز عبور (حداقل ۱۰ کاراکتر)'><button onclick='reg()'>ساخت حساب</button><p id='e' class='err'></p><a href='/login'>بازگشت به ورود</a></div><script>async function reg(){e.textContent='';let r=await fetch('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value,display_name:n.value})});let j=await r.json();if(!r.ok){e.textContent=j.detail||'خطا';return}location.href='/'}</script>"""

KNOWLEDGE_ADMIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>مدیریت دانش | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.wrap{max-width:1100px;margin:30px auto;padding:20px}.card{background:#fff;padding:18px;border-radius:12px;margin:10px 0}textarea,input{width:100%;box-sizing:border-box;padding:9px;margin:5px 0}button{padding:8px 12px;margin:3px}.u{background:#fef3c7}.v{background:#dcfce7}</style><div class='wrap'><h1>مدیریت دانش</h1><p>دانش جدید تا زمان تأیید، «تأییدنشده» است.</p><div id='list'>در حال بارگذاری...</div></div><script>
async function load(){let r=await fetch('/memory/knowledge?limit=200'),j=await r.json();if(!r.ok){list.textContent=j.detail||'خطا';return}list.innerHTML=(j.items||[]).map(x=>'<div class="card '+(x.verification_status==='verified'?'v':'u')+'"><b>'+esc(x.title)+'</b><div>'+esc(x.topic)+' | '+esc(x.verification_status)+'</div><input id="t'+x.id+'" value="'+esc(x.title)+'"><textarea id="c'+x.id+'">'+esc(x.content)+'</textarea><input id="s'+x.id+'" value="'+esc(x.source_url||'')+'"><button onclick="save('+x.id+')">ذخیره</button><button onclick="verify('+x.id+')">تأیید</button><button onclick="del('+x.id+')">حذف</button></div>').join('')||'دانشی ثبت نشده است'}function esc(v){return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}async function save(id){let r=await fetch('/memory/knowledge/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('t'+id).value,content:document.getElementById('c'+id).value,topic:'manual',source_url:document.getElementById('s'+id).value||null})});if(!r.ok)alert((await r.json()).detail||'خطا');load()}async function verify(id){let r=await fetch('/memory/knowledge/'+id+'/verify',{method:'POST'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}async function del(id){if(!confirm('حذف شود؟'))return;let r=await fetch('/memory/knowledge/'+id,{method:'DELETE'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}load()</script>"""

@app.get("/admin/knowledge", response_class=HTMLResponse)
def admin_knowledge_page(request: Request):
    require_admin(request)
    return HTMLResponse(KNOWLEDGE_ADMIN_HTML)

@app.get("/login", response_class=HTMLResponse)
def login_page():
    from .auth import has_users
    html=LOGIN_HTML
    if has_users():
        html=html.replace("<a id='register-link' href='/register'>ساخت اولین حساب</a>","")
    return HTMLResponse(html)

@app.get("/register", response_class=HTMLResponse)
def register_page():
    from .auth import has_users
    if has_users():
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(REGISTER_HTML)

@app.get("/auth/register/status")
def register_status():
    from .auth import has_users
    return {"open": not has_users()}

@app.post("/auth/register")
def auth_register(r: AuthRegisterRequest, request: Request):
    from .auth import has_users
    if has_users(): raise HTTPException(403,"Registration is closed after the first account. An administrator must create additional users.")
    try:
        user=create_account(r.username,r.password,r.display_name)
        if user["role"]=="admin":
            execute("UPDATE chat_sessions SET user_id=? WHERE user_id IS NULL",(user["id"],))
    except ValueError as exc: raise HTTPException(400,str(exc))
    response=JSONResponse({"user":user})
    response.set_cookie("myai_session",create_session(int(user["id"])),httponly=True,samesite="strict",secure=request.url.scheme=="https",max_age=86400,path="/")
    return response

@app.post("/auth/login")
def auth_login(r: AuthLoginRequest, request: Request):
    import time
    now=time.time(); _cleanup_login_failures(now)
    key=_login_key(request,r.username)
    count,started=_LOGIN_FAILURES.get(key,(0,now))
    if now-started>_LOGIN_FAILURE_WINDOW: count,started=0,now
    if count >= _LOGIN_FAILURE_LIMIT and now-started <= _LOGIN_FAILURE_WINDOW:
        raise HTTPException(429,"Too many failed login attempts. Try again later.")
    user=authenticate(r.username,r.password)
    if not user:
        count += 1
        _LOGIN_FAILURES[key]=(count,started)
        if count >= _LOGIN_FAILURE_LIMIT:
            raise HTTPException(429,"Too many failed login attempts. Try again later.")
        raise HTTPException(401,"نام کاربری یا رمز عبور نادرست است.")
    _LOGIN_FAILURES.pop(key,None)
    response=JSONResponse({"user":user})
    response.set_cookie("myai_session",create_session(int(user["id"])),httponly=True,samesite="strict",secure=request.url.scheme=="https",max_age=86400,path="/")
    return response

@app.post("/auth/logout")
def auth_logout(request: Request):
    token=request.cookies.get("myai_session")
    if token: revoke_session(token)
    response=JSONResponse({"ok":True})
    response.delete_cookie("myai_session",path="/")
    return response

@app.get("/auth/me")
def auth_me(request: Request): return {"user":require_user(request)}

@app.get("/admin/decision-log")
def admin_decision_log(request: Request, limit: int = 200):
    require_admin(request)
    return {"items": fetch_all("SELECT * FROM decision_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 1000)),))}

@app.get("/admin/audit")
def admin_audit(request: Request, limit: int=200):
    require_admin(request)
    return {"items":fetch_all("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",(max(1,min(limit,1000)),))}

@app.get("/admin/users")
def admin_users(request:Request):
    require_admin(request)
    return {"items":fetch_all("SELECT id,username,display_name,role,active,created_at FROM users ORDER BY id")}

@app.post("/admin/users")
def admin_create_user(r:AdminUserRequest,request:Request):
    admin=require_admin(request)
    try: user=create_account(r.username,r.password,r.display_name)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if user["role"]=="admin":
        execute("UPDATE users SET role='user' WHERE id=?",(user["id"],))
        user["role"]="user"
    audit(admin,"users","write","200",f"created:{user['username']}")
    return {"user":user}

@app.patch("/admin/users/{user_id}/active")
def admin_set_user_active(user_id:int,active:bool,request:Request):
    admin=require_admin(request)
    if user_id==admin["id"] and not active: raise HTTPException(400,"The active administrator cannot disable itself.")
    execute("UPDATE users SET active=? WHERE id=?",(1 if active else 0,user_id))
    audit(admin,"users","write","200",f"active:{user_id}:{active}")
    return {"ok":True}

@app.get("/admin/tools")
def admin_tools(request: Request):
    require_admin(request)
    return {"items":fetch_all("SELECT * FROM tool_permissions ORDER BY user_id,tool_name,action")}



@app.post("/chat/stream")
def chat_stream(r:ChatRequest, request:Request):
    user=require_user(request)
    if r.session_id is not None:
        if not fetch_all("SELECT id FROM chat_sessions WHERE id=? AND user_id=?",(r.session_id,user["id"])):
            raise HTTPException(404,"Chat session not found.")
        sid=r.session_id
    else:
        sid=execute("INSERT INTO chat_sessions(title,kind,user_id) VALUES(?,?,?)",((r.message or "گفتگوی جدید").strip()[:60],"chat",user["id"]))
    def generate():
        try:
            yield from agent.stream_chat(r.message,sid)
            audit(user,"chat","stream","200")
        except Exception as exc:
            audit(user,"chat","stream","502",str(exc))
            raise
    return StreamingResponse(generate(),media_type="text/plain; charset=utf-8")

@app.get("/memory/knowledge")
def knowledge_list(request: Request, status: str | None = None, limit: int = 200):
    user=require_user(request)
    limit=max(1,min(limit,1000))
    if user["role"] == "admin":
        if status:
            return {"items":fetch_all("SELECT * FROM knowledge WHERE verification_status=? ORDER BY id DESC LIMIT ?",(status,limit))}
        return {"items":fetch_all("SELECT * FROM knowledge ORDER BY id DESC LIMIT ?",(limit,))}
    return {"items":fetch_all(
        "SELECT * FROM knowledge WHERE verification_status IN ('verified','approved') ORDER BY id DESC LIMIT ?",
        (limit,),
    )}

@app.put("/memory/knowledge/{knowledge_id}")
def knowledge_update(knowledge_id:int, r:KnowledgeUpdateRequest, request:Request):
    user=require_admin(request)
    if not fetch_all("SELECT id FROM knowledge WHERE id=?",(knowledge_id,)): raise HTTPException(404,"Knowledge item not found.")
    import hashlib
    normalized = " ".join(f"{r.topic}\n{r.content}".replace("ي","ی").replace("ى","ی").replace("ك","ک").split()).casefold()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    execute("UPDATE knowledge SET title=?,content=?,topic=?,source_url=?,content_hash=?,verification_status='unverified',verified_at=NULL,verified_by=NULL,confidence=NULL WHERE id=?",(r.title,r.content,r.topic,r.source_url,content_hash,knowledge_id))
    audit(user,"knowledge","write","200",f"updated:{knowledge_id}")
    return {"updated":knowledge_id,"verification_status":"unverified"}

@app.delete("/memory/knowledge/{knowledge_id}")
def knowledge_delete(knowledge_id:int, request:Request):
    user=require_admin(request)
    execute("DELETE FROM knowledge WHERE id=?",(knowledge_id,))
    audit(user,"knowledge","delete","200",f"deleted:{knowledge_id}")
    return {"deleted":knowledge_id}

@app.post("/memory/knowledge/{knowledge_id}/verify")
def knowledge_verify(knowledge_id:int, request:Request):
    user=require_admin(request)
    rows=fetch_all("SELECT id,source_url,content_hash FROM knowledge WHERE id=?",(knowledge_id,))
    if not rows:
        raise HTTPException(404,"Knowledge item not found.")
    item=rows[0]
    source=str(item.get("source_url") or "").strip()
    if not source.startswith(("http://","https://")):
        raise HTTPException(400,"Verified knowledge requires a documented HTTP(S) source URL.")
    if not item.get("content_hash"):
        raise HTTPException(400,"Knowledge content hash is missing; save the item again before verification.")
    execute("UPDATE knowledge SET verification_status='verified',verified_at=CURRENT_TIMESTAMP,verified_by=? WHERE id=?",
            (user["id"],knowledge_id))
    audit(user,"knowledge","verify","200",f"verified:{knowledge_id}:source")
    return {"verified":knowledge_id,"verification_status":"verified","source_url":source}

@app.get("/memory/search/hybrid")
def memory_hybrid(q:str, request:Request, limit:int=8):
    require_user(request)
    return {"query":q,"items":hybrid_search(q,limit)}

@app.get("/models/health")
def models_health(request:Request):
    require_user(request)
    return model_health()

@app.get("/models/select")
def models_select(task:str, request:Request):
    require_user(request)
    return {"model":choose_model(task)}


@app.post("/voice/transcribe")
def voice_transcribe(r:VoiceTranscribeRequest, request:Request):
    user=require_user(request)
    result=transcribe(_voice_path(r.audio_path,True),_voice_path(r.model_path,True),r.language)
    audit(user,"voice","execute","200")
    return {"text":result}

@app.post("/voice/synthesize")
def voice_synthesize(r:VoiceSynthesizeRequest, request:Request):
    user=require_user(request)
    VOICE_ROOT.mkdir(parents=True,exist_ok=True)
    output_path=_voice_path(r.output_path,False)
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    result=synthesize(r.text,_voice_path(r.model_path,True),output_path)
    audit(user,"voice","execute","200")
    return {"path":result}

@app.get("/voice/status")
def voice_status_api(request:Request):
    require_user(request)
    return {**voice_status(), "engine": voice_engine_status()}

@app.get("/admin/readiness")
def admin_readiness(request: Request):
    require_admin(request)
    return build_readiness()

@app.get("/runtime/status")
def runtime_status_api(request: Request):
    require_user(request)
    return runtime_status()

@app.get("/scheduler/resources")
def scheduler_resources(request:Request):
    require_user(request)
    return resource_status()

@app.get("/web/fetch-policy")
def web_policy(url:str, request:Request):
    require_user(request)
    return web_fetch_policy(url)

@app.post("/backup/database")
def backup_db(r:BackupRequest, request:Request):
    user=require_admin(request)
    path=backup_database(r.path,r.password)
    audit(user,"database","backup","200",path)
    return {"path":path}

@app.post("/backup/export")
def backup_export(r:BackupRequest, request:Request):
    user=require_admin(request)
    path=export_database(r.path,r.password)
    audit(user,"database","export","200",path)
    return {"path":path}

@app.post("/backup/restore-database")
def backup_restore_database(r:ImportRequest, request:Request):
    user=require_admin(request)
    if not r.password or not r.destination:
        raise HTTPException(400,"password and destination are required.")
    path=restore_encrypted_backup(r.path,r.destination,r.password)
    audit(user,"database","restore","200",path)
    return {"path":path}

@app.post("/backup/import")
def backup_import(r:ImportRequest, request:Request):
    user=require_admin(request)
    result=import_encrypted_database(r.path,r.password) if r.password else import_database(r.path)
    audit(user,"database","import","200",r.path)
    return {"imported":result}

@app.post("/eval/retrieval/judgment")
def retrieval_judgment(query: str, knowledge_id: int, relevant: bool, score: float, request: Request):
    user=require_admin(request)
    if not fetch_all("SELECT id FROM knowledge WHERE id=?", (knowledge_id,)):
        raise HTTPException(404, "Knowledge item not found.")
    if not 0.0 <= float(score) <= 1.0:
        raise HTTPException(400, "score must be between 0 and 1.")
    execute("INSERT INTO retrieval_judgments(query,knowledge_id,relevant,score) VALUES(?,?,?,?)", (query, knowledge_id, int(bool(relevant)), float(score)))
    audit(user, "retrieval", "judge", "200", f"knowledge:{knowledge_id}")
    return {"status":"recorded"}

@app.get("/eval/retrieval")
def eval_retrieval_api(request:Request):
    require_admin(request)
    return eval_retrieval()

@app.get("/self-update/preview")
def self_update_preview_api(request:Request):
    require_admin(request)
    return preview_update()

@app.get("/self-update/status")
def self_update_status_api(request:Request):
    require_admin(request)
    return self_update_status()

@app.get("/self-repair/status")
def self_repair_status_api(request:Request):
    require_admin(request)
    return diagnose_local()

@app.post("/self-repair/propose")
def self_repair_propose_api(r:RepairRequest, request:Request):
    user=require_admin(request)
    result=propose_repair(r.issue)
    audit(user,"self-repair","write","200",f"proposal:{result['id']}")
    return result

@app.get("/self-repair/proposals")
def self_repair_proposals_api(request:Request):
    require_admin(request)
    return {"items": list_proposals()}

@app.get("/self-repair/proposals/{proposal_id}/diff")
def self_repair_diff_api(proposal_id:str, request:Request):
    require_admin(request)
    return proposal_diff(proposal_id)

@app.get("/self-repair/proposals/{proposal_id}")
def self_repair_proposal_api(proposal_id:str, request:Request):
    require_admin(request)
    return proposal_status(proposal_id)

@app.post("/self-repair/apply")
def self_repair_apply_api(r:RepairRequest, request:Request):
    user=require_admin(request)
    if not r.proposal_id:
        raise HTTPException(400,"proposal_id is required.")
    result=apply_repair(r.proposal_id,r.approved)
    audit(user,"self-repair","write","200",f"applied:{r.proposal_id}")
    return result

@app.post("/self-update/apply")
def self_update_apply_api(r:SelfUpdateRequest, request:Request):
    user=require_admin(request)
    health_url = str(r.health_url) if r.health_url else None
    if health_url:
        host=urlparse(health_url).hostname
        if host not in {"127.0.0.1","localhost","::1"}:
            raise HTTPException(400,"Self-update health URL must target the local host.")
    result=self_update_apply(health_url=health_url)
    audit(user,"self-update","write",str(result.get("status") or ("activated" if result.get("applied") else "blocked")),result.get("reason","") or result.get("details",""))
    return result

@app.put("/admin/tools")
def set_tool_permission(r:PermissionRequest, request:Request):
    user=require_admin(request)
    execute("""INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,?)
              ON CONFLICT(user_id,tool_name,action) DO UPDATE SET allowed=excluded.allowed,updated_at=CURRENT_TIMESTAMP""",
            (r.user_id,r.tool_name,r.action,1 if r.allowed else 0))
    audit(user,"tool-permissions","write","200",f"{r.user_id}:{r.tool_name}:{r.action}:{r.allowed}")
    return {"ok":True}


@app.get("/skills")
def skills_list(request:Request):
    require_user(request)
    return {"items":snapshot()}

@app.post("/skills")
def skills_create(name:str, request:Request, version:str="current"):
    require_user(request)
    return {"id":ensure_skill(name,version),"name":name,"version":version}

@app.post("/skills/evidence")
def skills_evidence(r:SkillEvidenceRequest, request:Request):
    user=require_admin(request)
    if r.kind not in {"test","benchmark","official_source"}:
        raise HTTPException(400,"Skill evidence must come from an executed test, benchmark, or official source.")
    if not r.details or not any(k in r.details for k in ("command","source_url","test_id","artifact")):
        raise HTTPException(400,"Evidence requires a command, source_url, test_id, or artifact reference.")
    eid=record_evidence(r.skill_id,r.kind,r.passed,r.details)
    audit(user,"skill-engine","execute","200",f"evidence:{r.skill_id}")
    return {"evidence_id":eid}

@app.post("/skills/revalidate")
def skills_revalidate(r:SkillRevalidateRequest, request:Request):
    user=require_admin(request)
    result=revalidate(r.skill_id,r.version)
    audit(user,"skill-engine","execute","200",f"revalidate:{r.skill_id}")
    return result

@app.get("/skills/reviews")
def skills_reviews(request:Request):
    require_admin(request)
    return {"items": review_snapshot()}


class SkillReviewRequest(BaseModel):
    skill_id: int
    outcome: str
    notes: str = ""


@app.post("/skills/reviews")
def skills_review(r:SkillReviewRequest, request:Request):
    user=require_admin(request)
    try:
        review_id=record_review(r.skill_id, int(user["id"]), r.outcome, r.notes)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(user,"skill-engine","write","200",f"review:{r.skill_id}:{r.outcome}")
    return {"review_id":review_id,"skill_id":r.skill_id,"outcome":r.outcome}

@app.get("/help",response_class=HTMLResponse)
def help(): return help_page()
@app.get("/chat/sessions")
def chat_sessions(request:Request):
    user=require_user(request)
    return {"sessions":fetch_all("SELECT id,title,kind,language,pinned,created_at,updated_at FROM chat_sessions WHERE user_id=? ORDER BY pinned DESC,updated_at DESC,id DESC",(user["id"],))}
@app.patch("/chat/sessions/{session_id}")
def update_chat_session(session_id:int,r:ChatRequest,request:Request):
    user=require_user(request)
    rows=fetch_all("SELECT id FROM chat_sessions WHERE id=? AND user_id=?",(session_id,user["id"]))
    if not rows: raise HTTPException(404,"Chat session not found")
    payload=r.message.strip()
    if payload:
        execute("UPDATE chat_sessions SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(payload[:80],session_id))
    return {"status":"updated","id":session_id}
@app.post("/chat/sessions/{session_id}/pin")
def pin_chat_session(session_id:int,request:Request):
    user=require_user(request)
    rows=fetch_all("SELECT id,pinned FROM chat_sessions WHERE id=? AND user_id=?",(session_id,user["id"]))
    if not rows: raise HTTPException(404,"Chat session not found")
    new_value=0 if rows[0]["pinned"] else 1
    execute("UPDATE chat_sessions SET pinned=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_value,session_id))
    return {"id":session_id,"pinned":bool(new_value)}
@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id:int,request:Request):
    user=require_user(request)
    rows=fetch_all("SELECT id FROM chat_sessions WHERE id=? AND user_id=?",(session_id,user["id"]))
    if not rows: raise HTTPException(404,"Chat session not found")
    execute("DELETE FROM conversations WHERE session_id=?",(session_id,))
    execute("DELETE FROM chat_sessions WHERE id=?",(session_id,))
    return {"status":"deleted","id":session_id}
@app.post("/chat/sessions")
def create_chat_session(r:ChatRequest,request:Request):
    user=require_user(request)
    sid=execute("INSERT INTO chat_sessions(title,user_id) VALUES(?,?)",((r.message or "گفتگوی جدید").strip()[:60],user["id"])); return {"id":sid}
@app.get("/chat/history")
def chat_history(request:Request,limit:int=100,session_id:int|None=None):
    user=require_user(request)
    limit=max(1,min(limit,500))
    if session_id is None:
        rows=fetch_all("SELECT c.role,c.content,c.created_at FROM conversations c JOIN chat_sessions s ON s.id=c.session_id WHERE s.user_id=? ORDER BY c.id DESC LIMIT ?",(user["id"],limit))
    else:
        rows=fetch_all("SELECT c.role,c.content,c.created_at FROM conversations c JOIN chat_sessions s ON s.id=c.session_id WHERE c.session_id=? AND s.user_id=? ORDER BY c.id DESC LIMIT ?",(session_id,user["id"],limit))
    rows.reverse(); return {"messages":rows}

@app.get("/help/updates")
def help_updates(status:str="pending"): return fetch_all("SELECT * FROM help_updates WHERE status=? ORDER BY id DESC",(status,))
@app.post("/help/ask")
def help_ask(r:ChatRequest, request:Request):
    require_user(request)
    try:
        low=r.message.lower(); component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
        return ask_help(r.message,component,agent.llm,learner.web)
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/help/local")
def help_local(component:str="chat"):
    return HTMLResponse("<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><title>My-AI — راهنمای محلی</title><style>body{font-family:Tahoma;max-width:900px;margin:30px auto;padding:20px;line-height:2;background:#f3f4f6}main{background:#fff;padding:25px;border-radius:14px}</style><main>"+local_help_html(component)+"</main></html>")

@app.post("/help/approve/{update_id}")
def help_approve(update_id:int,request:Request):
    require_admin(request)
    rows=fetch_all("SELECT * FROM help_updates WHERE id=? AND status='pending'",(update_id,))
    if not rows: raise HTTPException(404,"Pending help update not found.")
    proposal=rows[0].get("proposed_update") or ""
    if proposal.strip()=="NO_CHANGE":
        execute("UPDATE help_updates SET status='rejected' WHERE id=?",(update_id,)); return {"status":"rejected","update_id":update_id,"message":"No documentation change was proposed."}
    component=rows[0]["component"]
    if not apply_help_update(component, proposal):
        raise HTTPException(400,"The help component is not supported.")
    execute("UPDATE help_updates SET status='approved' WHERE id=?",(update_id,))
    return {"status":"approved","update_id":update_id,"message":"The approved help update was applied to the local help file."}
@app.post("/help/reject/{update_id}")
def help_reject(update_id:int,request:Request):
    require_admin(request)
    rows=fetch_all("SELECT * FROM help_updates WHERE id=? AND status='pending'",(update_id,))
    if not rows: raise HTTPException(404,"Pending help update not found.")
    execute("UPDATE help_updates SET status='rejected' WHERE id=?",(update_id,)); return {"status":"rejected","update_id":update_id}
@app.get("/self-diagnostics", response_class=HTMLResponse)
def self_diagnostics_page(request: Request):
    require_user(request)
    return HTMLResponse("""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>گزارش خودپایش | My-AI</title>
<style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0;color:#17202a}main{max-width:1100px;margin:auto;padding:22px}.hero{background:linear-gradient(135deg,#111827,#1e3a8a);color:white;padding:24px;border-radius:20px}.card{background:white;padding:18px;border-radius:14px;margin:14px 0;box-shadow:0 5px 20px #0000000b}.ok{border-right:6px solid #22c55e;background:#f0fdf4}.bad{border-right:6px solid #ef4444;background:#fef2f2}.fixed{border-right:6px solid #22c55e;background:#dcfce7}.meta{color:#64748b;font-size:13px}.back{display:inline-block;margin-top:12px;color:white}.row{padding:9px;border-bottom:1px solid #e5e7eb}</style>
<main><div class='hero'><h1>گزارش خودپایش و سلامت پروژه</h1><p>بررسی مداوم کد، تست‌ها، Git و سخت‌افزار</p><a class='back' href='/'>← بازگشت به صفحه اصلی</a></div><div id='out'><div class='card'>در حال دریافت گزارش...</div></div>
<script>
async function load(){let r=await fetch('/self-diagnostics/history?limit=20');let j=await r.json();let rows=j.reports||[];let out=document.getElementById('out');if(!rows.length){out.innerHTML='<div class="card">هنوز گزارشی ثبت نشده است.</div>';return}
let html='';
let seenErrors={};
rows.forEach(function(rep,i){let checks=rep.checks||{};let previous=rows[i+1];let fixed=[];if(previous){Object.keys(checks).forEach(function(k){if(previous.checks&&previous.checks[k]&&!previous.checks[k].ok&&checks[k].ok)fixed.push(k)})}
html+='<div class="card '+(rep.healthy?'ok':'bad')+'"><h2>'+(rep.healthy?'✓ وضعیت سالم':'⚠ نیازمند بررسی')+'</h2><div class="meta">'+(rep.timestamp||rep.created_at||'')+'</div>';
if(fixed.length)html+='<div class="card fixed"><b>✓ باگ/خطای برطرف‌شده در این بررسی</b><p>'+fixed.map(function(x){return x+' — برطرف شده'}).join('<br>')+'</p></div>';
Object.keys(checks).forEach(function(k){let x=checks[k]||{};let out=String(x.output||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');let errorKey=!x.ok?k+'|'+String(x.output||''):'';if(errorKey&&seenErrors[errorKey])return;if(errorKey)seenErrors[errorKey]=true;html+='<details class="row"><summary style="cursor:pointer">'+(x.ok?'🟢':'🔴')+' <b>'+k+'</b> — '+(x.ok?'سالم':'خطا / نیازمند بررسی')+'</summary>'+(x.output?'<pre style="direction:ltr;text-align:left;white-space:pre-wrap;overflow:auto;background:#111827;color:#f8fafc;padding:12px;border-radius:8px;margin-top:9px">'+out+'</pre>':'<div class="meta">جزئیات خطا ثبت نشده است.</div>')+'</details>'});
html+='</div>'});out.innerHTML=html}load();setInterval(load,30000);
</script></main></html>""")

@app.get("/self-diagnostics/report")
def self_diagnostics_report(request: Request):
    require_user(request)
    return latest_report() or {"status": "pending"}

@app.get("/self-diagnostics/history")
def self_diagnostics_history(request: Request, limit: int = 20):
    require_user(request)
    return {"reports": report_history(limit)}

@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model,"executor_mode":settings.exec_mode,"offline_strict":settings.offline_strict}

@app.get("/health/metrics")
def health_metrics():
    return {"status":"ok","offline_strict":settings.offline_strict,"inference":metrics_snapshot()["inference"]}

@app.post("/chat")
def chat(r:ChatRequest, request:Request):
    user=require_user(request)
    if r.session_id is not None and not fetch_all("SELECT id FROM chat_sessions WHERE id=? AND user_id=?",(r.session_id,user["id"])):
        raise HTTPException(404,"Chat session not found.")
    try:
        msg=r.message.strip(); low=msg.lower()
        intent=classify(msg)
        required_by_intent={"pentest_external":("security","execute"),"git_write":("github","write"),"self_update":("self-update","write"),"database_import":("database","write"),"code_execution":("code-execution","execute"),"self_repair":("self-repair","execute"),"learning":("learning","execute"),"coding":("code-generation","execute")}
        if intent.name in required_by_intent:
            tool,action=required_by_intent[intent.name]
            if not tool_allowed(user,tool,action):
                raise HTTPException(403,f"Tool permission denied: {tool}:{action}")
            if intent.name in {"code_execution","self_repair","self_update","git_write","database_import"} and not any(token in low for token in ("confirm","approve","approved","تایید","تأیید")):
                raise HTTPException(409,"Explicit confirmation required for high-risk intent: "+intent.name)
        aliases={"sql server":"SQL Server","sqlserver":"SQL Server","mssql":"SQL Server","mysql":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","آی او اس":"iOS","python":"Python","پایتون":"Python","php":"PHP","javascript":"JavaScript","js":"JavaScript","pentest":"Pentest","pen test":"Pentest","penetration testing":"Pentest","penetration test":"Pentest","پنتست":"Pentest","پن تست":"Pentest","تست نفوذ":"Pentest","امنیت":"Pentest"}
        requested=None
        for key,name in sorted(aliases.items(),key=lambda x:len(x[0]),reverse=True):
            if key.isascii():
                if re.search(r"(?<![a-z0-9])"+re.escape(key)+r"(?![a-z0-9])",low): requested=name; break
            elif re.search(r"(?<!\w)"+re.escape(key)+r"(?!\w)",low,re.UNICODE):
                requested=name; break
        learn_intent=("یاد بگیر" in low or "یادگیری" in low or "learn" in low or "go learn" in low or "start learning" in low); sid=r.session_id or execute("INSERT INTO chat_sessions(title,kind,language,user_id) VALUES(?,?,?,?)",(msg[:60] or "گفتگوی جدید","learning" if learn_intent else "chat",requested,user["id"])); policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
        if security_words:
            if not tool_allowed(user,"security","execute"):
                raise HTTPException(403,"Tool permission denied: security:execute")
            if fix_requested and user["role"]!="admin":
                raise HTTPException(403,"Security remediation requires administrator approval.")
        help_intent=("راهنما" in low or "چطور وصل" in low or "چطور استفاده" in low or "how do i" in low or "how to" in low or "setup" in low)
        if help_intent:
            component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
            return {"type":"help","answer":"راهنمای هوشمند آماده شد.","data":ask_help(msg,component,agent.llm,learner.web)}
        image_words=("تصویر بساز","عکس بساز","عکس طراحی کن","تصویر طراحی کن","تصویر ایجاد کن","عکس ایجاد کن","مانگا","مانگا طراحی","کمیک","comic","manga","draw an image","generate an image","create an image","design an image")
        image_intent=any(x in low for x in image_words)
        if image_intent:
            if not tool_allowed(user,"image-generation","execute"):
                raise HTTPException(403,"Tool permission denied: image-generation:execute")
            try:
                image_result=generate_image(msg)
            except ImageGenerationError as exc:
                raise HTTPException(502,str(exc))
            answer="تصویر با موفقیت تولید شد."
            image_url=image_result["url"] if "url" in image_result else f"/image/file/{image_result['filename']}"
            # Keep a compact textual history entry; the UI renders the returned image separately.
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"user",msg))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"assistant",answer+" "+image_url))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(sid,))
            return {"type":"image","answer":answer,"data":{**image_result,"url":image_url},"session_id":sid}

        code_words=("برنامه بنویس","کد بنویس","برام برنامه","write a program","write code","program","build an app","create an app"); code_intent=any(x in low for x in code_words)
        if security_words:
            if code_intent:
                language=requested or "Python"; generated=learner.generate_program(msg,language); result=learner.security_assessment_code(generated["code"],language,fix_requested); result["generated_project"]=generated; result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"
                dynamic_status=(result.get("dynamic") or {}).get("status")
                answer=("Static assessment completed; local dynamic DAST requires an approved sandbox." if dynamic_status=="sandbox_required" else ("Security assessment completed." if not fix_requested else "Security assessment and remediation completed."))
                return {"type":"security","answer":answer,"data":result}
            path=None
            for prefix in ("مسیر:","آدرس:","path:","url:","project:","پروژه:"):
                if prefix in msg: path=msg.split(prefix,1)[1].strip().strip('"').strip("'"); break
            if not path:
                m=re.search(r"https?://[^\s]+",msg)
                if m:path=m.group(0).rstrip(".,)")
            if path:
                if path.lower().startswith(("http://","https://")): result=learner.security_assessment_url(path,r.headers if hasattr(r,"headers") else None); result["note"]="External targets are report-only; remediation is not applied remotely."
                else: result=learner.security_assessment_path(path,fix_requested)
                result["mode"]="external_report" if path.lower().startswith(("http://","https://")) else ("pentest_and_fix" if fix_requested else "pentest_report")
                dynamic_status=(result.get("dynamic") or {}).get("status")
                answer="External DAST completed for the explicitly supplied target." if path.lower().startswith(("http://","https://")) else ("Static assessment completed; local dynamic DAST requires an approved sandbox." if dynamic_status=="sandbox_required" else "Security assessment completed for the explicitly supplied target.")
                return {"type":"security","answer":answer,"data":result}
        if learn_intent:
            language=resolve_learning_target(msg, requested or "Python")
            language=canonical_language(language)
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"user",msg))
            scheduler.interval_seconds=settings.scheduler_interval_seconds
            requested_languages=[]
            for key,name in sorted(aliases.items(),key=lambda x:len(x[0]),reverse=True):
                matched = bool(
                    re.search(r"(?<![a-z0-9])"+re.escape(key)+r"(?![a-z0-9])",low)
                    if key.isascii() else re.search(r"(?<!\w)"+re.escape(key)+r"(?!\w)",low,re.UNICODE)
                )
                if matched and name not in requested_languages:
                    requested_languages.append(name)
            if not requested_languages:
                requested_languages=[requested or "Python"]
            languages=[]
            for target in requested_languages:
                target_language=canonical_language(resolve_learning_target(msg,target))
                if target_language not in languages:
                    languages.append(target_language)
                    scheduler.start(target_language, sid)
            label="، ".join(languages)
            answer=f"یادگیری {label} در پس‌زمینه شروع شد." if len(languages)==1 else f"یادگیری همزمان {label} در پس‌زمینه شروع شد."
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"assistant",answer)); execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(sid,))
            return {"type":"learning","answer":answer,"data":{"status":"started","languages":languages,"language":languages[0],"interval_seconds":3600,"session_id":sid},"session_id":sid}
        if code_intent:
            language=requested or "Python"
            return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
        if any(x in low for x in ("تایید آپدیت","تأیید آپدیت","تایید بروزرسانی","تأیید بروزرسانی","تایید به روزرسانی","تأیید به روزرسانی","confirm update","approve update","apply update")):
            if user["role"] != "admin":
                raise HTTPException(403,"Self-update requires administrator approval.")
        return {"type":"chat","answer":agent.chat(msg,sid),"session_id":sid}
    except HTTPException:
        raise
    except Exception as e: raise HTTPException(502,str(e))

@app.post("/learn/url")
def learn_url(r:URLRequest, request:Request):
    require_user(request)
    try:return learner.study_url(str(r.url),r.topic)
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/learning/start")
def learning_start(r:LanguageRequest, request:Request):
    require_user(request)
    result=learner.start(r.language)
    if result.get("status")=="started": scheduler.start(r.language, result.get("session_id"))
    return result
@app.post("/learning/step")
def learning_step(r:LanguageRequest, request:Request):
    require_user(request)
    try:return learner.learn_next(r.language)
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/tools/catalog")
def tools_catalog(request:Request):
    require_user(request)
    return tool_catalog()
@app.get("/tools/doctor")
def tools_doctor(request:Request,language:str|None=None):
    require_user(request)
    return tool_doctor(language)
@app.post("/tools/project")
def tools_project(r:ToolRequest,request:Request):
    require_user(request)
    if r.operation.strip().lower() != "test" and not r.confirmed:
        raise HTTPException(409,"Explicit confirmation is required for project tool operations.")
    return run_project_tool(r.language,r.operation,r.cwd,r.timeout)
@app.post("/tools/python")
def tools_python(r:PythonToolRequest,request:Request):
    require_user(request)
    if not r.confirmed:
        raise HTTPException(409,"Explicit confirmation is required for Python execution.")
    return run_python_snippet(r.code)
@app.get("/tools/sqlserver/schema")
def tools_sqlserver_schema(request:Request,limit:int=500):
    require_user(request)
    return sqlserver_schema(limit)
@app.post("/tools/sqlserver/query")
def tools_sqlserver_query(r:SQLQueryRequest,request:Request):
    require_user(request)
    return sqlserver_query(r.sql,r.limit)
@app.get("/tools/mysql/schema")
def tools_mysql_schema(request:Request,limit:int=500):
    require_user(request)
    return mysql_schema(limit)
@app.post("/tools/mysql/query")
def tools_mysql_query(r:SQLQueryRequest,request:Request):
    require_user(request)
    return mysql_query(r.sql,r.limit)

@app.get("/tools/sqlite/schema")
def tools_sqlite_schema(request:Request,path:str):
    require_user(request)
    return sqlite_schema(path)
@app.post("/tools/sqlite/query")
def tools_sqlite_query(r:SQLiteQueryRequest,request:Request):
    require_user(request)
    return sqlite_query(r.path,r.sql,r.limit)

@app.get("/learning/status")
def learning_status(request:Request, language:str|None=None):
    require_user(request)
    summary=learner.status(language)
    summary.update(learner.detailed_status(language))
    return summary
@app.post("/learning/practice")
def practice(r:ChatRequest, request:Request):
    require_user(request)
    try:return learner.practice(r.message)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/code/run")
def code_run(r:CodeRequest, request:Request):
    require_user(request)
    if not r.confirmed:
        raise HTTPException(409,"Explicit confirmation is required for code execution.")
    return learner.validate_code(r.code)
@app.post("/code/generate")
def code_generate(r:ProgramRequest, request:Request):
    require_user(request)
    try:return learner.generate_program(r.request,r.language)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/security/scan")
def security_scan(r:SecurityRequest,request:Request):
    user=require_user(request)
    if r.fix and user["role"]!="admin": raise HTTPException(403,"Security remediation requires administrator approval.")
    try:
        if r.target_url:return learner.security_assessment_url(r.target_url,r.headers)
        if r.project_path:
            if r.project_path.lower().startswith(("http://","https://")):return learner.security_assessment_url(r.project_path,r.headers)
            return learner.security_assessment_path(r.project_path,r.fix)
        if r.code:return learner.security_assessment_code(r.code,r.language,r.fix)
        return learner.security_scan_latest_generated(r.fix)
    except Exception as e: raise HTTPException(400,str(e))
@app.get("/security/history")
def security_history(request:Request,limit:int=20):
    require_user(request)
    return learner.security.history(max(1,min(limit,200)))
@app.post("/git/login")
def git_login():
    try:
        if GitHubConnector.gh_available():
            if not GitHubConnector.gh_logged_in():
                GitHubConnector.gh_login()
                return {"authenticated":False,"pending":True,"method":"gh","token_source":GitHubConnector.token_source(),"message":"مرورگر برای ورود GitHub باز شد. بعد از تأیید، «بررسی اتصال» را بزنید."}
            return {"authenticated":True,"pending":False,"method":"gh","token_source":GitHubConnector.token_source(),"message":"ورود GitHub قبلاً انجام شده است."}
        if not GitHubConnector.oauth_available():
            raise HTTPException(503,"GitHub CLI نصب نیست و MYAI_GITHUB_CLIENT_ID نیز تنظیم نشده است.")
        if GitHubConnector.token_status():
            return {"authenticated":True,"pending":False,"method":"oauth","token_source":GitHubConnector.token_source(),"message":"اتصال GitHub قبلاً برقرار است."}
        flow=GitHubConnector.oauth_start()
        return {"authenticated":False,"pending":True,"method":"oauth",**flow,"message":"صفحه ورود GitHub باز شد. کد نمایش‌داده‌شده را در GitHub تأیید کنید."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502,str(e))

@app.get("/git/login/status")
def git_login_status():
    try:
        if GitHubConnector.gh_available() and GitHubConnector.gh_logged_in():
            return {"authenticated":True,"pending":False,"method":"gh","token_source":GitHubConnector.token_source()}
        if GitHubConnector.token_status():
            return {"authenticated":True,"pending":False,"method":"oauth","token_source":GitHubConnector.token_source()}
        if not GitHubConnector.oauth_available():
            return {"authenticated":False,"pending":False,"method":"none","message":"OAuth Client ID تنظیم نشده است."}
        result=GitHubConnector.oauth_status()
        result["authenticated"]=result.get("status")=="authenticated"
        result["pending"]=result.get("status")=="pending"
        result["method"]="oauth"
        return result
    except Exception as e:
        raise HTTPException(502,str(e))

@app.post("/git/logout")
def git_logout():
    try:
        GitHubConnector.save_token("")
        exe=GitHubConnector._gh_executable()
        if exe:
            r=subprocess.run([exe,"auth","logout","--hostname","github.com"],input="y\n",capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if r.returncode != 0:
                raise RuntimeError((r.stderr or r.stdout or "GitHub logout failed").strip())
        return {"authenticated":False,"message":"از GitHub خارج شدی."}
    except Exception as e:
        raise HTTPException(502,str(e))

@app.get("/git/connection")
def git_connection():
    try:
        identity=GitHubConnector().whoami()
        return {"connected":True,"authenticated":True,"login":identity.get("login"),"name":identity.get("name"),"token_source":GitHubConnector.token_source()}
    except Exception as e:
        return {"connected":False,"authenticated":GitHubConnector.token_status(),"error":str(e)}
@app.post("/git/token")
def git_token(r:ChatRequest):
    token=r.message.strip()
    if token and len(token)<20: raise HTTPException(400,"توکن GitHub نامعتبر است.")
    try:
        if not token:
            GitHubConnector.save_token("")
            return {"saved":False,"authenticated":False}
        GitHubConnector.save_token(token)
        c=GitHubConnector(token=token)
        try:
            identity=c.whoami()
        except Exception as e:
            if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
                if e.status_code == 401:
                    GitHubConnector.save_token("")
                    raise HTTPException(401, f"GitHub Token رد شد: {e.message}")
                if e.status_code == 403:
                    raise HTTPException(403, f"GitHub Token احراز هویت شد اما GitHub دسترسی این درخواست را رد کرد: {e.message}")
                raise HTTPException(502, f"GitHub API خطای {e.status_code} داد: {e.message}")
            raise HTTPException(502, f"اتصال به GitHub برقرار نشد: {e}")
        return {
            "saved":True,
            "authenticated":True,
            "login":identity.get("login"),
            "name":identity.get("name"),
        }
    except HTTPException:
        raise
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            raise HTTPException(e.status_code if e.status_code in (400,401,403,404,409,422,429) else 502, f"GitHub API: {e.message}")
        raise HTTPException(502,f"GitHub connector error: {e}")

@app.delete("/git/token")
def delete_git_token():
    try:
        GitHubConnector.save_token("")
        return {"saved":False,"authenticated":False}
    except Exception as e: raise HTTPException(500,str(e))

@app.get("/git/whoami")
def git_whoami():
    try:
        c=GitHubConnector()
        token_source=GitHubConnector.token_source()
        if token_source == "none":
            raise HTTPException(401,"GitHub Token تنظیم نشده است.")
        identity=c.whoami()
        return {"authenticated":True,"login":identity.get("login"),"name":identity.get("name"),"token_source":token_source}
    except HTTPException: raise
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            raise HTTPException(e.status_code if e.status_code in (401,403,404,429) else 502, f"GitHub API: {e.message}")
        raise HTTPException(502,f"اتصال به GitHub برقرار نشد: {e}")

@app.get("/git/token/diagnostics")
def git_token_diagnostics():
    try:
        c=GitHubConnector()
        d=c.token_diagnostics()
        return {"authenticated":False,**d}
    except Exception as e:
        raise HTTPException(500,f"GitHub token diagnostics error: {e}")

@app.get("/git/check")
def git_check(repository:str|None=None):
    cfg=get_github_settings()
    if not cfg.get("api_url"):
        return {"authenticated":False,"repository":repository,"status":"not_configured","message":"GitHub API URL در تنظیمات ثبت نشده است."}
    try:
        c=GitHubConnector()
    except RuntimeError as e:
        return {"authenticated":False,"repository":repository,"status":"not_configured","message":str(e)}
    token_source=GitHubConnector.token_source()
    if token_source == "none":
        return {"authenticated":False,"repository":repository,"status":"no_token","message":"GitHub Token تنظیم نشده است."}
    if not repository:
        try:
            identity=c.whoami()
            return {"authenticated":True,"status":"ok","login":identity.get("login"),"token_source":token_source,"message":"GitHub Token معتبر است."}
        except Exception as e:
            if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
                return {"authenticated":False,"status":"github_auth_error","http_status":e.status_code,"token_source":token_source,"github_message":e.message}
            return {"authenticated":False,"status":"network_error","token_source":token_source,"message":str(e)}
    try:
        data=c.repo(repository)
        identity=data.get("owner") or {}
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            if e.status_code == 401:
                return {"authenticated":False,"repository":repository,"status":"invalid_token","http_status":401,"token_source":token_source,"github_message":e.message,"message":"GitHub این Token را رد کرد؛ ممکن است revoke شده یا واقعاً نامعتبر باشد."}
            if e.status_code == 403:
                return {"authenticated":False,"repository":repository,"status":"auth_forbidden","http_status":403,"token_source":token_source,"github_message":e.message,"message":"GitHub Token شناخته شد، اما سیاست یا دسترسی GitHub این درخواست را رد کرد."}
            return {"authenticated":False,"repository":repository,"status":"github_auth_error","http_status":e.status_code,"token_source":token_source,"github_message":e.message,"message":f"GitHub خطای {e.status_code} در احراز هویت برگرداند."}
        return {"authenticated":False,"repository":repository,"status":"network_error","token_source":token_source,"message":f"اتصال به GitHub برقرار نشد: {e}"}
    try:
        return {
            "authenticated":True,
            "repository":repository,
            "status":"ok",
            "login":identity.get("login"),
            "private":bool(data.get("private")),
            "permissions":data.get("permissions") or {},
            "message":"Token معتبر است و به مخزن دسترسی دارد.",
        }
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            if e.status_code == 404:
                return {"authenticated":True,"repository":repository,"status":"repo_forbidden_or_missing","http_status":404,"login":identity.get("login"),"github_message":e.message,"message":"Token معتبر است، اما GitHub این مخزن را برای این Token قابل دسترسی نمی‌داند."}
            if e.status_code == 403:
                return {"authenticated":True,"repository":repository,"status":"repo_forbidden","http_status":403,"login":identity.get("login"),"github_message":e.message,"message":"Token معتبر است، اما GitHub دسترسی این مخزن یا permission لازم را رد کرد."}
            return {"authenticated":True,"repository":repository,"status":"github_error","http_status":e.status_code,"login":identity.get("login"),"github_message":e.message,"message":f"GitHub خطای {e.status_code} داد."}
        return {"authenticated":True,"repository":repository,"status":"network_error","login":identity.get("login"),"message":f"اتصال به GitHub برقرار نشد: {e}"}

@app.get("/git/repo")
def git_repo(repository:str):
    try:
        data=GitHubConnector().repo(repository)
        data["connected"]=True
        data["authenticated"]=GitHubConnector.token_status()
        return data
    except Exception as e:
        msg=str(e)
        code=404 if "GitHub API 404" in msg else 502
        raise HTTPException(code,msg)
@app.get("/git/tree")
def git_tree(repository:str,ref:str="HEAD"): return GitHubConnector().tree(repository,ref)
@app.get("/git/file")
def git_file(request:Request,repository:str,path:str,ref:str|None=None):
    require_user(request)
    normalized=path.replace("\\","/")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized or any(part==".." for part in normalized.split("/")):
        raise HTTPException(400,"Invalid repository path.")
    return GitHubConnector().file(repository,normalized,ref)
@app.get("/git/issues")
def git_issues(repository:str,state:str="open"): return GitHubConnector().issues(repository,state)
@app.get("/git/pulls")
def git_pulls(repository:str,state:str="open"): return GitHubConnector().pull_requests(repository,state)
@app.get("/git/branches")
def git_branches(repository:str): return GitHubConnector().branches(repository)
@app.post("/git/branch")
def git_branch(r:GitRequest, request:Request):
    require_admin(request)
    return GitHubConnector().create_branch(r.repository,r.branch or "",r.ref or "main",True)
@app.put("/git/file")
def git_update_file(r:GitRequest, request:Request):
    require_admin(request)
    if not r.path or r.content is None or not r.message: raise HTTPException(400,"path, content and message are required")
    return GitHubConnector().update_file(r.repository,r.path,r.content,r.message,r.branch or "main",True)
@app.get("/languages")
def languages(): return {"languages":list(LANGUAGE_CURRICULA.keys())}
@app.post("/projects/plan")
def project_plan(r:ProjectRequest, request:Request):
    require_user(request)
    try:return {"tasks":agent.plan_project(r.goal)}
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/memory/search")
def memory_search(q:str,request:Request,limit:int=8):
    require_user(request)
    from .memory import recall; return recall(q,limit)
@app.get("/projects/tasks")
def project_tasks(request:Request):
    require_user(request)
    return fetch_all("SELECT * FROM project_tasks ORDER BY id")
@app.post("/scheduler/start")
def scheduler_start(r:SchedulerRequest, request:Request):
    require_user(request)
    interval=get_int("learning.interval_seconds",r.interval_seconds) if get_bool("learning.fast_enabled",False) else r.interval_seconds
    if not 60<=interval<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=interval; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":interval}
@app.get("/scheduler/status")
def scheduler_status(request:Request):
    require_user(request)
    return scheduler.status()
@app.post("/learning/learn")
def learning_learn(r:LearnRequest, request:Request):
    require_user(request)
    interval=get_int("learning.interval_seconds",r.interval_seconds) if get_bool("learning.fast_enabled",False) else r.interval_seconds
    if not 60<=interval<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=interval; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":interval}
@app.post("/scheduler/stop")
def scheduler_stop(request:Request):
    require_user(request)
    scheduler.stop_learning()
    return {"status":"stopped","languages":[x["language"] for x in scheduler.status().get("workers",[]) if x.get("status")=="stopping"]}


from .settings_feature import install as _install_settings_features
_install_settings_features(app)
