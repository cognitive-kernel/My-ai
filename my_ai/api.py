from __future__ import annotations
from contextlib import asynccontextmanager
import os
import sys
import subprocess
import json
import re
import time
import logging
import uuid
from urllib.parse import urlparse
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request,UploadFile
from pydantic import BaseModel
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse,StreamingResponse,Response
from fastapi.staticfiles import StaticFiles
from .agent import Agent
from .command_policy import parse_command
from .config import settings
from .settings_store import get_bool, get_int, get_github_settings, set_setting
from .curriculum import canonical_language,LANGUAGE_CURRICULA
from .db import fetch_all,init_db,execute
from .learner import LearningEngine
from .dynamic_learning import resolve_learning_target
from .router import classify
from .observability import configure_logging, request_log
from .scheduler import StudyScheduler
from .ui import page
from .feature_routes import register_routes
from .learning_resilience import install as install_learning_resilience
from .ui_extensions import install_ui_extensions
from .help import page as help_page, ask_help, local_help_html, apply_help_update
from .git_connector import GitHubConnector
from .auth import authenticate, audit, audit_event, create_account, create_session, current_user, require_admin, revoke_session, require_user, tool_allowed
from .platform import backup_database, choose_model, eval_retrieval, export_database, hybrid_search, import_database, model_health, resource_status, voice_status, web_fetch_policy
from .self_update import status as self_update_status, apply_confirmed_update as self_update_apply, preview_update
from .self_repair import diagnose_local, propose_repair, apply_repair, proposal_status
from .skill_engine import ensure_skill, record_evidence, revalidate, snapshot, record_review, review_snapshot
from .voice import status as voice_engine_status, transcribe, synthesize
from .metrics import snapshot as metrics_snapshot, record_http_request, record_http_error
from .platform import import_encrypted_database, restore_encrypted_backup
from .self_repair import list_proposals, proposal_diff
from .self_diagnostics import SelfDiagnosticsMonitor, latest_report, report_history, paginated_report_history
from .tooling import catalog as tool_catalog, doctor as tool_doctor, run_project_tool, run_python_snippet, sqlserver_query, sqlserver_schema, mysql_query, mysql_schema, sqlite_query, sqlite_schema
from .runtime_prerequisites import startup_check, runtime_status
from .local_files import WORKSPACE_ROOT
from .settings_feature import shutdown_course_workers
from .access_policy import is_public_path, TOOL_RULES, PATH_ACTIONS
from .config import assert_write_allowed
from .policy_engine import policy
_TOOL_RULES = TOOL_RULES
_PATH_ACTIONS = PATH_ACTIONS
from .api_models import (
    AdminUserRequest, AuthLoginRequest, AuthRegisterRequest, BackupRequest, ChatRequest,
    CodeRequest, GitRequest, ImportRequest, KnowledgeUpdateRequest, LanguageRequest,
    LearnRequest, PermissionRequest, ProjectRequest, ProjectBuildRequest, ProgramRequest, PythonToolRequest,
    RepairRequest, SchedulerRequest, SecurityRequest, SelfUpdateRequest, SkillEvidenceRequest,
    SkillRevalidateRequest, SQLQueryRequest, SQLiteQueryRequest, ToolRequest, URLRequest,
    VoiceSynthesizeRequest, VoiceTranscribeRequest,
)
from .readiness import build_readiness
from .project_builder import build_project, project_status

logger = logging.getLogger("my_ai.api")
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
    shutdown_course_workers()
configure_logging()
startup_check()
app=FastAPI(title="My-AI",version="0.2.0",description="Local-first personal learning and coding agent.",lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")

register_routes(app, scheduler, require_user, audit)
install_learning_resilience()
install_ui_extensions(app)

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
    path = request.url.path
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    user = current_user(request)
    response: Response | None = None
    request_body = await request.body()
    if not is_public_path(path) and not user:
        if "application/json" in request.headers.get("accept", "").lower():
            response = JSONResponse({"detail": "Authentication required.", "request_id": request_id}, status_code=401)
        else:
            response = RedirectResponse("/login", status_code=303)
        response.headers["X-Request-ID"] = request_id
        audit_event(None, "auth", "authenticate", "401", request_id=request_id, input_data=request_body, extra={"method": request.method, "path": path})
        return response
    read_only = os.getenv("MYAI_READ_ONLY", "false").strip().lower() == "true"
    decision = policy.decide(user=user, method=request.method, path=path, read_only=read_only)
    if not decision.allowed:
        status = 423 if decision.reason == "read_only" else 403
        audit_event(user, decision.tool or "policy", decision.action or request.method.lower(), str(status), request_id=request_id, input_data=request_body, extra={"method": request.method, "path": path, "reason": decision.reason})
        response = JSONResponse({"detail": f"Policy denied: {decision.reason}", "request_id": request_id}, status_code=status)
        response.headers["X-Request-ID"] = request_id
        return response
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        record_http_error(path)
        audit_event(user, decision.tool or path, decision.action or request.method.lower(), "500", request_id=request_id, input_data=request_body, error="unhandled_request_exception", extra={"method": request.method, "path": path})
        logger.exception("Unhandled request error", extra={"request_id": request_id, "method": request.method, "path": path})
        raise
    finally:
        duration = time.perf_counter() - started
        status_code = response.status_code if response is not None else 500
        record_http_request(request.method, path, status_code, duration)
        logging.getLogger("my_ai.http").info("request", extra=request_log(request_id=request_id, method=request.method, path=path, status=status_code, duration_ms=duration * 1000, user_id=(user or {}).get("id")))
    response.headers["X-Request-ID"] = request_id
    if user and response.status_code >= 400 and get_bool("learning.personal_experience", True):
        try:
            active = fetch_all("SELECT id,language,session_id,current_topic FROM learning_workers WHERE status IN ('running','retrying','paused') ORDER BY id DESC LIMIT 1")
            if active and active[0].get("current_topic"):
                learner.record_experience(active[0]["language"], active[0]["current_topic"], "error", f"{request.method} {path}", "عملیات در زمان یادگیری با خطا مواجه شد.", f"HTTP {response.status_code}", active[0].get("session_id"))
        except Exception:
            logger.exception("Failed to store learning personal experience")
    if user and path != "/auth/logout":
        action = decision.action or {"GET": "read", "POST": "execute", "PUT": "write", "PATCH": "write", "DELETE": "write"}.get(request.method, request.method.lower())
        audit_event(
            user,
            decision.tool or path,
            action,
            str(response.status_code),
            request_id=request_id,
            input_data=request_body,
            output_data=getattr(response, "body", None),
            extra={
                "method": request.method,
                "path": path,
                "content_type": response.headers.get("content-type"),
                "streaming": isinstance(response, StreamingResponse),
            },
        )
    return response
agent=Agent(); learner=LearningEngine()
VOICE_ROOT=Path("data/voice").resolve()
def _voice_path(value:str, must_exist:bool=False) -> str:
    path=Path(value).expanduser().resolve()
    try: path.relative_to(VOICE_ROOT)
    except ValueError: raise HTTPException(400,"Voice paths must stay under data/voice.")
    if must_exist and not path.is_file(): raise HTTPException(404,"Voice input/model file not found.")
    return str(path)
def _validate_chat_attachments(items):
    result=[]
    for item in list(items or [])[:10]:
        raw_path=str(item.get("path") or "").strip()
        if not raw_path:
            raise HTTPException(400,"Attachment path is required.")
        path=Path(raw_path).expanduser().resolve()
        try:
            path.relative_to(WORKSPACE_ROOT)
        except ValueError:
            raise HTTPException(400,"Chat attachments must stay inside the My-AI workspace.")
        if not path.is_file():
            raise HTTPException(404,f"Attachment not found: {path.name}")
        size=path.stat().st_size
        if size > 100 * 1024 * 1024:
            raise HTTPException(413,"Each chat attachment is limited to 100 MiB.")
        result.append({
            "path":str(path),
            "name":str(item.get("name") or path.name),
            "size":int(item.get("size") or size),
            "mime_type":str(item.get("mime_type") or "application/octet-stream"),
        })
    return result

def _save_chat_attachments(session_id, attachments, conversation_id=None):
    if not attachments:
        return
    for item in attachments:
        execute(
            "INSERT INTO chat_attachments(conversation_id,session_id,name,path,size,mime_type) VALUES(?,?,?,?,?,?)",
            (conversation_id,session_id,item["name"],item["path"],item["size"],item["mime_type"]),
        )

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

KNOWLEDGE_ADMIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>مدیریت دانش | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.wrap{max-width:1200px;margin:24px auto;padding:20px}.card{background:#fff;padding:16px;border-radius:12px;margin:10px 0;box-shadow:0 1px 3px #0001}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}textarea,input,select{width:100%;box-sizing:border-box;padding:9px;margin:5px 0}button{padding:8px 12px;margin:3px;cursor:pointer}.u{border-right:5px solid #f59e0b}.v{border-right:5px solid #16a34a}.meta{font-size:12px;color:#555}.sources{background:#f8fafc;padding:8px;border-radius:8px;margin-top:8px}.danger{color:#b91c1c}</style><div class='wrap'><h1>مدیریت دانش</h1><p>هر رکورد قبل از استفاده در retrieval باید provenance و وضعیت verification مشخص داشته باشد.</p><div class='card'><h3>افزودن دانش</h3><div class='grid'><input id='nt' placeholder='عنوان'><input id='topic' placeholder='موضوع'><input id='src' placeholder='منبع HTTP(S)'></div><textarea id='nc' placeholder='محتوا'></textarea><button onclick='add()'>افزودن</button></div><div id='list'>در حال بارگذاری...</div></div><script>
function esc(v){return String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
async function load(){let r=await fetch('/memory/knowledge?limit=200'),j=await r.json();if(!r.ok){list.textContent=j.detail||'خطا';return}list.innerHTML=(j.items||[]).map(x=>'<div class="card '+(x.verification_status==='verified'?'v':'u')+'"><h3>'+esc(x.title)+'</h3><div>'+esc(x.topic)+' | وضعیت: '+esc(x.verification_status)+'</div><div class="meta">hash: '+esc(x.content_hash)+' | confidence: '+esc(x.confidence??'—')+' | verified_by: '+esc(x.verified_by??'—')+'</div><input id="t'+x.id+'" value="'+esc(x.title)+'"><textarea id="c'+x.id+'">'+esc(x.content)+'</textarea><input id="s'+x.id+'" value="'+esc(x.source_url||'')+'"><button onclick="save('+x.id+')">ذخیره و invalidate verification</button><button onclick="verify('+x.id+')">تأیید منبع</button><button onclick="audit('+x.id+')">Audit</button><button onclick="del('+x.id+')">حذف منطقی</button><div id="a'+x.id+'" class="sources"></div></div>').join('')||'دانشی ثبت نشده است'}
async function add(){let r=await fetch('/memory/knowledge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:nt.value,content:nc.value,topic:topic.value,source_url:src.value||null})});if(!r.ok)alert((await r.json()).detail||'خطا');else{nt.value=topic.value=src.value=nc.value='';load()}}
async function save(id){let r=await fetch('/memory/knowledge/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('t'+id).value,content:document.getElementById('c'+id).value,topic:'manual',source_url:document.getElementById('s'+id).value||null})});if(!r.ok)alert((await r.json()).detail||'خطا');load()}
async function verify(id){let r=await fetch('/memory/knowledge/'+id+'/verify',{method:'POST'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}
async function audit(id){let r=await fetch('/memory/knowledge/'+id+'/audit');let j=await r.json();document.getElementById('a'+id).innerHTML='<b>Audit</b><pre>'+esc(JSON.stringify(j.items||[],null,2))+'</pre>'}
async function del(id){if(!confirm('حذف شود؟'))return;let r=await fetch('/memory/knowledge/'+id,{method:'DELETE'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}load()</script>"""

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

@app.post("/memory/knowledge")
def knowledge_create(r:KnowledgeUpdateRequest, request:Request):
    user=require_admin(request)
    import hashlib
    if not r.title.strip() or not r.content.strip() or not r.topic.strip():
        raise HTTPException(400,"title, topic and content are required.")
    normalized = " ".join(f"{r.topic}\n{r.content}".replace("ي","ی").replace("ى","ی").replace("ك","ک").split()).casefold()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    knowledge_id = execute(
        "INSERT INTO knowledge(topic,title,content,source_url,content_hash,verification_status) VALUES(?,?,?,?,?,'unverified')",
        (r.topic,r.title,r.content,r.source_url,content_hash),
    )
    execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",(knowledge_id,user["id"],"create",f"source_url={r.source_url or ''}"))
    audit(user,"knowledge","write","201",f"created:{knowledge_id}")
    return {"id":knowledge_id,"verification_status":"unverified","content_hash":content_hash}

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
    execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",(knowledge_id,user["id"],"update",f"source_url={r.source_url or ''}"))
    audit(user,"knowledge","write","200",f"updated:{knowledge_id}")
    return {"updated":knowledge_id,"verification_status":"unverified"}


@app.get("/memory/knowledge/{knowledge_id}/audit")
def knowledge_audit(knowledge_id:int, request:Request, limit:int=50):
    require_admin(request)
    return {"items":fetch_all("SELECT id,knowledge_id,user_id,action,details,created_at FROM knowledge_audit WHERE knowledge_id=? ORDER BY id DESC LIMIT ?",(knowledge_id,max(1,min(limit,200))))}
@app.delete("/memory/knowledge/{knowledge_id}")
def knowledge_delete(knowledge_id:int, request:Request):
    user=require_admin(request)
    execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",(knowledge_id,user["id"],"delete","knowledge item soft-deleted"))
    execute("UPDATE knowledge SET verification_status='deleted',verified_at=NULL,verified_by=NULL,confidence=NULL WHERE id=?",(knowledge_id,))
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
    execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",(knowledge_id,user["id"],"verify",f"source_url={source}"))
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
    model_path = r.model_path.strip() or os.getenv("WHISPER_MODEL_PATH", "").strip()
    if not model_path:
        raise HTTPException(503, "WHISPER_MODEL_PATH is not configured.")
    result=transcribe(_voice_path(r.audio_path,True),_voice_path(model_path,True),r.language)
    audit(user,"voice","execute","200")
    return {"text":result}

@app.post("/voice/synthesize")
def voice_synthesize(r:VoiceSynthesizeRequest, request:Request):
    user=require_user(request)
    model_path = r.model_path.strip() or os.getenv("PIPER_MODEL_PATH", "").strip()
    if not model_path:
        raise HTTPException(503, "PIPER_MODEL_PATH is not configured.")
    VOICE_ROOT.mkdir(parents=True,exist_ok=True)
    output_path=_voice_path(r.output_path,False)
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    result=synthesize(r.text,_voice_path(model_path,True),output_path)
    audit(user,"voice","execute","200")
    return {"path":result}

@app.post("/voice/upload")
def voice_upload(file:UploadFile, request:Request):
    user=require_user(request)
    if not file.filename:
        raise HTTPException(400, "Voice file name is required.")
    safe_name = Path(file.filename).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".wav",".webm",".ogg",".mp3",".m4a",".mp4"}:
        raise HTTPException(400, "Unsupported voice recording format.")
    VOICE_ROOT.mkdir(parents=True,exist_ok=True)
    target = (VOICE_ROOT / f"recording-{uuid.uuid4().hex}{suffix}").resolve()
    try:
        target.relative_to(VOICE_ROOT)
    except ValueError:
        raise HTTPException(400, "Invalid voice path.")
    data = file.file.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Voice recording is limited to 25 MiB.")
    assert_write_allowed(str(target))
    target.write_bytes(data)
    audit(user,"voice","write","201",str(target))
    return {"path":str(target),"local_path":str(target)}

@app.get("/voice/file")
def voice_file(path:str, request:Request):
    require_user(request)
    candidate = Path(path).expanduser().resolve()
    try:
        candidate.relative_to(VOICE_ROOT)
    except ValueError:
        raise HTTPException(400, "Voice paths must stay under data/voice.")
    if not candidate.is_file():
        raise HTTPException(404, "Voice file not found.")
    from fastapi.responses import FileResponse
    return FileResponse(candidate)

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


SKILLS_ADMIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Skill Engine | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6}.wrap{max-width:1200px;margin:24px auto}.card{background:#fff;padding:16px;border-radius:12px;margin:10px 0}.score{display:inline-block;padding:5px 9px;border-radius:8px;background:#eef2ff}.ev{background:#f8fafc;padding:8px;margin:6px 0;border-radius:8px}button{padding:7px 11px;margin:3px}</style><div class='wrap'><h1>Skill Engine</h1><p>Knowledge coverage و verified skill score مستقل‌اند؛ verification فقط با evidence معتبر انجام می‌شود.</p><div id='list'>در حال بارگذاری...</div></div><script>
function esc(v){return String(v??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
async function load(){let r=await fetch('/skills'),j=await r.json();if(!r.ok){list.textContent=j.detail||'خطا';return}list.innerHTML=(j.items||[]).map(x=>'<div class="card"><h2>'+esc(x.name)+' <small>v'+esc(x.version)+'</small></h2><span class="score">Knowledge coverage: '+esc(x.knowledge_coverage_score)+'</span> <span class="score">Verified skill: '+esc(x.verified_skill_score)+'</span><p>State: '+esc(x.verification_state)+' | review due: '+esc(x.review_due)+'</p><button onclick="rev('+x.id+')">Revalidate</button><details><summary>Evidence ('+esc(x.evidence_count)+')</summary>'+((x.evidence||[]).map(e=>'<div class="ev"><b>'+esc(e.kind)+'</b> | passed='+esc(e.passed)+' | '+esc(e.created_at)+'<pre>'+esc(JSON.stringify(e.details,null,2))+'</pre></div>').join('')||'بدون evidence')+'</details></div>').join('')||'Skill ثبت نشده است'}
async function rev(id){let version=prompt('نسخه فعلی skill را وارد کنید:','current');if(version===null)return;let r=await fetch('/skills/revalidate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({skill_id:Number(id),current_version:version})});let j=await r.json();if(!r.ok)alert(j.detail||'خطا');load()}load()</script>"""

@app.get("/admin/skills", response_class=HTMLResponse)
def admin_skills_page(request:Request):
    require_admin(request)
    return HTMLResponse(SKILLS_ADMIN_HTML)

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
    if not r.details:
        raise HTTPException(400,"Evidence details are required.")
    if r.kind == "official_source" and not str(r.details.get("source_url") or "").strip():
        raise HTTPException(400,"Official-source evidence requires a non-empty source_url.")
    if r.kind in {"test","benchmark"} and (not str(r.details.get("command") or "").strip() or "artifact" not in r.details):
        raise HTTPException(400,"Executed evidence requires a command and artifact.")
    eid=record_evidence(r.skill_id,r.kind,r.passed,r.details)
    audit(user,"skill-engine","execute","200",f"evidence:{r.skill_id}")
    return {"evidence_id":eid}

@app.post("/skills/revalidate")
def skills_revalidate(r:SkillRevalidateRequest, request:Request):
    user=require_admin(request)
    result=revalidate(r.skill_id,r.version)
    audit(user,"skill-engine","execute","200",f"revalidate:{r.skill_id}")
    return result

@app.post("/skills/{skill_id}/sandbox-test")
def skill_sandbox_test(skill_id:int, r:PythonToolRequest, request:Request):
    user=require_admin(request)
    if not r.confirmed:
        raise HTTPException(409,"Explicit confirmation is required for a skill sandbox test.")
    if settings.exec_mode not in {"container", "remote"}:
        raise HTTPException(409,"Skill verification requires the container or remote sandbox executor; subprocess mode is not accepted as verification evidence.")
    if not fetch_all("SELECT id FROM skills WHERE id=?",(skill_id,)):
        raise HTTPException(404,"Skill not found.")
    result=run_python_snippet(r.code)
    passed=result.get("return_code")==0 and not result.get("timed_out") and result.get("sandbox_mode") in {"container", "remote-container"}
    evidence=record_evidence(
        skill_id,
        "benchmark",
        bool(passed),
        {
            "command":"sandbox:python",
            "artifact":json.dumps(result,ensure_ascii=False)[:12000],
            "sandbox_mode":result.get("sandbox_mode","unknown"),
            "skill_score": 100.0 if passed else 0.0,
            "reliability_score": 100.0 if passed else 0.0,
        },
    )
    audit(user,"skill-engine","execute", "200" if passed else "422", f"sandbox:{skill_id}:passed={passed}")
    return {"passed":passed,"evidence_id":evidence,"result":result}
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
        rows=fetch_all("SELECT c.id,c.role,c.content,c.created_at FROM conversations c JOIN chat_sessions s ON s.id=c.session_id WHERE s.user_id=? ORDER BY c.id DESC LIMIT ?",(user["id"],limit))
    else:
        rows=fetch_all("SELECT c.role,c.content,c.created_at FROM conversations c JOIN chat_sessions s ON s.id=c.session_id WHERE c.session_id=? AND s.user_id=? ORDER BY c.id DESC LIMIT ?",(session_id,user["id"],limit))
    rows.reverse();
    attachment_query="SELECT id,conversation_id,name,path,size,mime_type,created_at FROM chat_attachments WHERE session_id=? ORDER BY id"
    attachments=fetch_all(attachment_query,(session_id,)) if session_id is not None else []
    for item in attachments:
        item["download_url"]="/files/download?path="+__import__("urllib.parse",fromlist=["quote"]).quote(item["path"],safe="")
        item.pop("path",None)
    return {"messages":rows,"attachments":attachments}

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
<style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0;color:#17202a}main{max-width:1100px;margin:auto;padding:22px}.hero{background:linear-gradient(135deg,#111827,#1e3a8a);color:white;padding:24px;border-radius:20px}.card{background:white;padding:18px;border-radius:14px;margin:14px 0;box-shadow:0 5px 20px #0000000b}.ok{border-right:6px solid #22c55e;background:#f0fdf4}.bad{border-right:6px solid #ef4444;background:#fef2f2}.fixed{border-right:6px solid #22c55e;background:#dcfce7}.meta{color:#64748b;font-size:13px}.back{display:inline-block;margin-top:12px;color:white}.row{padding:9px;border-bottom:1px solid #e5e7eb}.pager{display:flex;gap:8px;align-items:center;justify-content:center;margin:20px 0}.pager button{padding:9px 14px;border:1px solid #cbd5e1;border-radius:8px;background:white;cursor:pointer}.pager button:disabled{opacity:.45;cursor:not-allowed}.page-info{font-weight:bold}</style>
<main><div class='hero'><h1>گزارش خودپایش و سلامت پروژه</h1><p>بررسی مداوم کد، تست‌ها، Git و سخت‌افزار</p><a class='back' href='/'>← بازگشت به صفحه اصلی</a></div><div id='out'><div class='card'>در حال دریافت گزارش...</div></div><div id='pager' class='pager' hidden><button id='prev' onclick='changePage(-1)'>قبلی</button><span id='pageInfo' class='page-info'></span><button id='next' onclick='changePage(1)'>بعدی</button></div>
<script>
let currentPage=1;
function localDateTime(value){
  if(!value)return '';
  const d=new Date(value);
  if(Number.isNaN(d.getTime()))return value;
  try{return new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'short',timeStyle:'medium',hourCycle:'h23'}).format(d)}
  catch(e){return d.toLocaleString('fa-IR')}
}
async function load(page=currentPage){
  const r=await fetch('/self-diagnostics/history?page='+page+'&page_size=10');
  const j=await r.json();
  const rows=j.reports||[],out=document.getElementById('out');
  currentPage=j.page||page;
  if(!r.ok){out.innerHTML='<div class="card bad">'+(j.detail||'خطا در دریافت گزارش‌ها')+'</div>';return}
  if(!rows.length){
    out.innerHTML='<div class="card">هنوز گزارشی ثبت نشده است.</div>';
    document.getElementById('pager').hidden=true;
    return;
  }
  let html='';
  let seenErrors={};
  rows.forEach(function(rep,i){
    let checks=rep.checks||{},previous=rows[i+1],fixed=[];
    if(previous){Object.keys(checks).forEach(function(k){if(previous.checks&&previous.checks[k]&&!previous.checks[k].ok&&checks[k].ok)fixed.push(k)})}
    html+='<div class="card '+(rep.healthy?'ok':'bad')+'"><h2>'+(rep.healthy?'✓ وضعیت سالم':'⚠ نیازمند بررسی')+'</h2><div class="meta">'+localDateTime(rep.timestamp||rep.created_at)+'</div>';
    if(fixed.length)html+='<div class="card fixed"><b>✓ باگ/خطای برطرف‌شده در این بررسی</b><p>'+fixed.map(function(x){return x+' — برطرف شده'}).join('<br>')+'</p></div>';
    Object.keys(checks).forEach(function(k){let x=checks[k]||{},outText=String(x.output||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');let errorKey=!x.ok?k+'|'+String(x.output||''):'';if(errorKey&&seenErrors[errorKey])return;if(errorKey)seenErrors[errorKey]=true;html+='<details class="row"><summary style="cursor:pointer">'+(x.ok?'🟢':'🔴')+' <b>'+k+'</b> — '+(x.ok?'سالم':'خطا / نیازمند بررسی')+'</summary>'+(x.output?'<pre style="direction:ltr;text-align:left;white-space:pre-wrap;overflow:auto;background:#111827;color:#f8fafc;padding:12px;border-radius:8px;margin-top:9px">'+outText+'</pre>':'<div class="meta">جزئیات خطا ثبت نشده است.</div>')+'</details>'});
    html+='</div>';
  });
  out.innerHTML=html;
  const pager=document.getElementById('pager');
  pager.hidden=(j.total_pages||1)<=1;
  document.getElementById('pageInfo').textContent='صفحه '+currentPage+' از '+(j.total_pages||1);
  document.getElementById('prev').disabled=currentPage<=1;
  document.getElementById('next').disabled=currentPage>=(j.total_pages||1);
}
function changePage(delta){const next=currentPage+delta;if(next<1)return;load(next).catch(()=>{})}
load();setInterval(function(){load(currentPage).catch(()=>{})},30000);
</script></main></html>""")

@app.get("/self-diagnostics/report")
def self_diagnostics_report(request: Request):
    require_user(request)
    return latest_report() or {"status": "pending"}

@app.get("/self-diagnostics/history")
def self_diagnostics_history(request: Request, page: int = 1, page_size: int = 10, limit: int | None = None):
    require_user(request)
    if limit is not None:
        return {"reports": report_history(limit)}
    return paginated_report_history(page, page_size)

@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model,"executor_mode":settings.exec_mode,"offline_strict":settings.offline_strict}

@app.get("/health/metrics")
def health_metrics():
    return {"status":"ok","offline_strict":settings.offline_strict,**metrics_snapshot()}

def _learning_command(r: ChatRequest, request: Request, user=None):
    user = user or require_user(request)
    if r.session_id is not None and not fetch_all(
        "SELECT id FROM chat_sessions WHERE id=? AND user_id=? AND kind='learning'",
        (r.session_id, user["id"]),
    ):
        raise HTTPException(404, "Learning session not found.")
    msg = r.message.strip()
    if not msg:
        raise HTTPException(400, "Learning command is required.")
    intent = classify(msg)
    if intent.name != "learning":
        raise HTTPException(400, "این صفحه فقط دستورات یادگیری را اجرا می‌کند.")
    if not tool_allowed(user, "learning", "execute"):
        raise HTTPException(403, "Tool permission denied: learning:execute")
    requested = intent.args.get("language") if isinstance(intent.args, dict) else None
    requested = canonical_language(requested) if requested else None
    language = canonical_language(resolve_learning_target(msg, requested or "Python"))
    sid = r.session_id or execute(
        "INSERT INTO chat_sessions(title,kind,language,user_id) VALUES(?,?,?,?)",
        (msg[:60] or "یادگیری جدید", "learning", language, user["id"]),
    )
    execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (sid, "user", msg))
    scheduler.interval_seconds = settings.scheduler_interval_seconds
    scheduler.start(language, sid)
    answer = f"یادگیری {language} در پس‌زمینه شروع شد."
    execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (sid, "assistant", answer))
    execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
    return {
        "type": "learning",
        "answer": answer,
        "data": {
            "status": "started",
            "languages": [language],
            "language": language,
            "interval_seconds": settings.scheduler_interval_seconds,
            "session_id": sid,
            "custom_courses": [],
        },
        "session_id": sid,
    }

@app.post("/learning/command")
def learning_command(r: ChatRequest, request: Request):
    return _learning_command(r, request)

@app.post("/chat")
def chat(r:ChatRequest, request:Request):
    user=require_user(request)
    if r.session_id is not None and not fetch_all("SELECT id FROM chat_sessions WHERE id=? AND user_id=?",(r.session_id,user["id"])):
        raise HTTPException(404,"Chat session not found.")
    try:
        msg=r.message.strip(); low=msg.lower()
        attachments=_validate_chat_attachments(r.attachments)
        intent=classify(msg)
        # Learning and image generation have dedicated pages/endpoints. Never execute
        # execute either operation through the general chat endpoint.
        if intent.name == "learning":
            raise HTTPException(409, "یادگیری فقط در صفحه «پیشرفت و یادگیری» انجام می‌شود.")
        if intent.name == "image_generation":
            raise HTTPException(409, "ساخت تصویر فقط در صفحه «ساخت تصویر» انجام می‌شود.")
        required_by_intent={"pentest_external":("security","execute"),"git_write":("github","write"),"self_update":("self-update","write"),"database_import":("database","write"),"code_execution":("code-execution","execute"),"self_repair":("self-repair","execute"),"coding":("code-generation","execute")}
        if intent.name in required_by_intent:
            tool,action=required_by_intent[intent.name]
            if not tool_allowed(user,tool,action):
                raise HTTPException(403,f"Tool permission denied: {tool}:{action}")
            if intent.name in {"code_execution","self_repair","self_update","git_write","database_import"} and not any(token in low for token in ("confirm","approve","approved","تایید","تأیید")):
                raise HTTPException(409,"Explicit confirmation required for high-risk intent: "+intent.name)
        requested=intent.args.get("language") if isinstance(intent.args, dict) else None
        requested=canonical_language(requested) if requested else None
        learn_intent=intent.name == "learning"; sid=r.session_id or execute("INSERT INTO chat_sessions(title,kind,language,user_id) VALUES(?,?,?,?)",(msg[:60] or "گفتگوی جدید","learning" if learn_intent else "chat",requested,user["id"])); sid=r.session_id or execute("INSERT INTO chat_sessions(title,kind,language,user_id) VALUES(?,?,?,?)",(msg[:60] or "گفتگوی جدید","learning" if learn_intent else "chat",requested,user["id"])); _save_chat_attachments(sid,attachments); policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
        if security_words:
            if not tool_allowed(user,"security","execute"):
                raise HTTPException(403,"Tool permission denied: security:execute")
            if fix_requested and user["role"]!="admin":
                raise HTTPException(403,"Security remediation requires administrator approval.")
        help_intent=intent.name == "help"
        if help_intent:
            component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
            return {"type":"help","answer":"راهنمای هوشمند آماده شد.","data":ask_help(msg,component,agent.llm,learner.web)}
        code_intent=intent.name == "coding"
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
            raise HTTPException(409, "یادگیری فقط در صفحه «پیشرفت و یادگیری» انجام می‌شود.")
        if code_intent:
            language=requested or "Python"
            if policy.build:
                if not any(token in low for token in ("confirm","approve","approved","تایید","تأیید")):
                    raise HTTPException(409,"Explicit confirmation required before building the application.")
                return {"type":"project","answer":"Application project build completed.","data":build_project(msg,language,timeout=300,repair_attempts=2)}
            return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
        if any(x in low for x in ("تایید آپدیت","تأیید آپدیت","تایید بروزرسانی","تأیید بروزرسانی","تایید به روزرسانی","تأیید به روزرسانی","confirm update","approve update","apply update")):
            if user["role"] != "admin":
                raise HTTPException(403,"Self-update requires administrator approval.")
        answer=agent.chat(msg,sid,attachments=attachments)
        user_message=fetch_all("SELECT id FROM conversations WHERE session_id=? AND role='user' ORDER BY id DESC LIMIT 1",(sid,))
        if attachments and user_message:
            execute("UPDATE chat_attachments SET conversation_id=? WHERE session_id=? AND conversation_id IS NULL",(user_message[0]["id"],sid))
        return {"type":"chat","answer":answer,"session_id":sid,"attachments":[{**item,"download_url":"/files/download?path="+__import__("urllib.parse",fromlist=["quote"]).quote(item["path"],safe="")} for item in attachments]}
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

@app.get("/learning/experience/settings")
def learning_experience_settings(request:Request):
    require_user(request)
    return {"enabled": get_bool("learning.personal_experience", True)}

@app.patch("/learning/experience/settings")
def learning_experience_settings_update(request:Request, enabled:bool):
    require_user(request)
    set_setting("learning.personal_experience", "true" if enabled else "false")
    return {"enabled": bool(enabled)}

@app.get("/learning/experiences")
def learning_experiences(request:Request, language:str, topic:str, limit:int=20):
    require_user(request)
    return {"enabled": get_bool("learning.personal_experience", True), "items": [dict(x) for x in learner.personal_experiences(language, topic, limit)]}

@app.get("/learning/status")
def learning_status(request:Request, language:str|None=None):
    require_user(request)
    summary=learner.status(language)
    summary.update(learner.detailed_status(language))
    # Custom Course progress is exposed by /learning/active and its own UI;
    # never leak its internal custom_course:<id> tracks into the standard
    # learning status response, even if a stale/legacy learner implementation
    # still reports them.
    def _standard_track(item):
        return not str(item.get("language") or "").strip().lower().startswith("custom_course:")
    summary["languages"]=[item for item in summary.get("languages",[]) if _standard_track(item)]
    summary["courses"]=[item for item in summary.get("courses",[]) if _standard_track(item)]
    summary["sessions"]=[item for item in summary.get("sessions",[]) if _standard_track(item)]
    summary["available_languages"]=[
        item for item in summary.get("available_languages",[])
        if not str(item or "").strip().lower().startswith("custom_course:")
    ]
    return JSONResponse(summary, headers={"Cache-Control":"no-store","Pragma":"no-cache"})
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
@app.post("/projects/build")
def projects_build(r:ProjectBuildRequest, request:Request):
    user=require_user(request)
    if not r.confirmed:
        raise HTTPException(409,"Explicit confirmation is required before building and executing a project toolchain.")
    if not tool_allowed(user,"code-generation","execute"):
        raise HTTPException(403,"Tool permission denied: code-generation:execute")
    try:return build_project(r.goal,r.language,timeout=max(30,min(int(r.timeout),600)),repair_attempts=max(0,min(int(r.repair_attempts),3)))
    except Exception as e: raise HTTPException(502,str(e))

@app.get("/projects/status")
def projects_status(path:str, request:Request):
    require_user(request)
    try:return project_status(path)
    except Exception as e: raise HTTPException(400,str(e))

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
