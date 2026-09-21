from __future__ import annotations
from contextlib import asynccontextmanager
import re
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse,StreamingResponse
from pydantic import BaseModel,HttpUrl,Field
from .agent import Agent
from .command_policy import parse_command
from .config import settings
from .curriculum import canonical_language,LANGUAGE_CURRICULA
from .db import fetch_all,init_db,execute
from .learner import LearningEngine
from .scheduler import StudyScheduler
from .ui import page
from .help import page as help_page, ask_help, local_help_html
from .git_connector import GitHubConnector
from .auth import authenticate, audit, create_account, create_session, current_user, require_admin, revoke_session, require_user, tool_allowed
from .platform import backup_database, choose_model, eval_retrieval, export_database, hybrid_search, import_database, model_health, resource_status, self_update_apply, self_update_status, voice_status, web_fetch_policy
from .skill_engine import ensure_skill, record_evidence, revalidate, snapshot
from .voice import status as voice_engine_status, transcribe, synthesize
from .llm import create_llm

scheduler=StudyScheduler()
@asynccontextmanager
async def lifespan(_):
    init_db()
    scheduler.start_review_monitor()
    active=fetch_all("SELECT language FROM learning_sessions WHERE status='started' ORDER BY id DESC LIMIT 1")
    if active: scheduler.start(active[0]["language"])
    yield
    scheduler.stop()
app=FastAPI(title="My-AI",version="0.2.0",description="Local-first personal learning and coding agent.",lifespan=lifespan)

_PUBLIC_PATHS = {"/", "/login", "/register", "/auth/register", "/auth/login", "/auth/logout", "/health", "/openapi.json", "/docs", "/redoc"}
_TOOL_RULES = (("/git/","github"),("/security/","security"),("/code/run","code-execution"),("/scheduler/","scheduler"),("/learning/","learning"),("/backup/","database"),("/voice/","voice"),("/skills","skill-engine"),("/models/","models"),("/memory/search","memory"),("/web/","web"),("/projects/","projects"),("/eval/","eval"),("/self-update/","self-update"))
_LOGIN_FAILURES: dict[str, tuple[int, float]] = {}


@app.middleware("http")
async def auth_and_audit_middleware(request: Request, call_next):
    path=request.url.path
    user=current_user(request)
    if path not in _PUBLIC_PATHS and not path.startswith("/docs/") and not user:
        if "application/json" in request.headers.get("accept","").lower():
            return JSONResponse({"detail":"Authentication required."},status_code=401)
        return RedirectResponse("/login",status_code=303)
    if user and user["role"] != "admin":
        for prefix,tool in _TOOL_RULES:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                action="read" if request.method=="GET" else "write" if request.method in {"PUT","PATCH","DELETE"} else "execute"
                if not tool_allowed(user,tool,action) and not tool_allowed(user,tool,"execute"):
                    return JSONResponse({"detail":f"Tool permission denied: {tool}:{action}"},status_code=403)
                break
    response=await call_next(request)
    if user and path!="/auth/logout":
        action={"GET":"read","POST":"execute","PUT":"write","PATCH":"write","DELETE":"write"}.get(request.method,request.method.lower())
        audit(user,path,action,str(response.status_code))
    return response

agent=Agent(); learner=LearningEngine()
class ChatRequest(BaseModel): message:str; session_id:int|None=None
class AuthRegisterRequest(BaseModel): username:str; password:str; display_name:str=""
class AuthLoginRequest(BaseModel): username:str; password:str
class KnowledgeUpdateRequest(BaseModel): title:str; content:str; topic:str; source_url:str|None=None
class BackupRequest(BaseModel): path:str
class ImportRequest(BaseModel): path:str
class PermissionRequest(BaseModel): user_id:int; tool_name:str; action:str; allowed:bool
class AdminUserRequest(BaseModel): username:str; password:str; display_name:str=""; active:bool=True
class SkillEvidenceRequest(BaseModel): skill_id:int; kind:str; passed:bool; details:dict[str,object]={}
class SkillRevalidateRequest(BaseModel): skill_id:int; version:str
class VoiceTranscribeRequest(BaseModel): audio_path:str; model_path:str; language:str="fa"
class VoiceSynthesizeRequest(BaseModel): text:str; model_path:str; output_path:str
class URLRequest(BaseModel): url:HttpUrl; topic:str="Python"
class ProjectRequest(BaseModel): goal:str
class CodeRequest(BaseModel): code:str
class ProgramRequest(BaseModel): request:str; language:str="Python"
class LanguageRequest(BaseModel): language:str="Python"
class SecurityRequest(BaseModel): project_path:str|None=None; target_url:str|None=None; code:str|None=None; language:str="Python"; fix:bool=False; headers:dict[str,str]=Field(default_factory=dict)
class GitRequest(BaseModel): repository:str; path:str|None=None; ref:str|None=None; branch:str|None=None; content:str|None=None; message:str|None=None; allow_write:bool=False
class SchedulerRequest(BaseModel): language:str="Python"; interval_seconds:int=3600
class LearnRequest(BaseModel): language:str="Python"; interval_seconds:int=3600

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

LOGIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ورود | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.box{max-width:420px;margin:10vh auto;background:#fff;padding:28px;border-radius:16px}input,button{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:9px;border:1px solid #ccc}button{cursor:pointer;background:#111827;color:#fff}.err{color:#b91c1c}</style><div class='box'><h1>ورود به My-AI</h1><input id='u' placeholder='نام کاربری'><input id='p' type='password' placeholder='رمز عبور'><button onclick='login()'>ورود</button><p id='e' class='err'></p><a href='/register'>ساخت اولین حساب</a></div><script>async function login(){e.textContent='';let r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let j=await r.json();if(!r.ok){e.textContent=j.detail||'خطا';return}location.href='/'}</script>"""
REGISTER_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ساخت حساب | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.box{max-width:420px;margin:10vh auto;background:#fff;padding:28px;border-radius:16px}input,button{width:100%;box-sizing:border-box;padding:12px;margin:7px 0;border-radius:9px;border:1px solid #ccc}button{cursor:pointer;background:#111827;color:#fff}.err{color:#b91c1c}.note{background:#ecfdf5;padding:10px;border-radius:8px}</style><div class='box'><h1>ساخت حساب My-AI</h1><p class='note'>اگر هنوز هیچ حسابی ساخته نشده باشد، این حساب به‌صورت خودکار <b>ادمین اصلی</b> می‌شود و به همه ابزارها دسترسی خواهد داشت.</p><input id='n' placeholder='نام نمایشی'><input id='u' placeholder='نام کاربری'><input id='p' type='password' placeholder='رمز عبور (حداقل ۱۰ کاراکتر)'><button onclick='reg()'>ساخت حساب</button><p id='e' class='err'></p><a href='/login'>بازگشت به ورود</a></div><script>async function reg(){e.textContent='';let r=await fetch('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value,display_name:n.value})});let j=await r.json();if(!r.ok){e.textContent=j.detail||'خطا';return}location.href='/'}</script>"""

KNOWLEDGE_ADMIN_HTML="""<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>مدیریت دانش | My-AI</title><style>body{font-family:Tahoma;background:#f3f4f6;margin:0}.wrap{max-width:1100px;margin:30px auto;padding:20px}.card{background:#fff;padding:18px;border-radius:12px;margin:10px 0}textarea,input{width:100%;box-sizing:border-box;padding:9px;margin:5px 0}button{padding:8px 12px;margin:3px}.u{background:#fef3c7}.v{background:#dcfce7}</style><div class='wrap'><h1>مدیریت دانش</h1><p>دانش جدید تا زمان تأیید، «تأییدنشده» است.</p><div id='list'>در حال بارگذاری...</div></div><script>
async function load(){let r=await fetch('/memory/knowledge?limit=200'),j=await r.json();if(!r.ok){list.textContent=j.detail||'خطا';return}list.innerHTML=(j.items||[]).map(x=>'<div class="card '+(x.verification_status==='verified'?'v':'u')+'"><b>'+esc(x.title)+'</b><div>'+esc(x.topic)+' | '+esc(x.verification_status)+'</div><input id="t'+x.id+'" value="'+esc(x.title)+'"><textarea id="c'+x.id+'">'+esc(x.content)+'</textarea><input id="s'+x.id+'" value="'+esc(x.source_url||'')+'"><button onclick="save('+x.id+')">ذخیره</button><button onclick="verify('+x.id+')">تأیید</button><button onclick="del('+x.id+')">حذف</button></div>').join('')||'دانشی ثبت نشده است'}function esc(v){return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}async function save(id){let r=await fetch('/memory/knowledge/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('t'+id).value,content:document.getElementById('c'+id).value,topic:'manual',source_url:document.getElementById('s'+id).value||null})});if(!r.ok)alert((await r.json()).detail||'خطا');load()}async function verify(id){let r=await fetch('/memory/knowledge/'+id+'/verify',{method:'POST'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}async function del(id){if(!confirm('حذف شود؟'))return;let r=await fetch('/memory/knowledge/'+id,{method:'DELETE'});if(!r.ok)alert((await r.json()).detail||'خطا');load()}load()</script>"""

@app.get("/admin/knowledge", response_class=HTMLResponse)
def admin_knowledge_page(request: Request):
    require_admin(request)
    return HTMLResponse(KNOWLEDGE_ADMIN_HTML)

@app.get("/login", response_class=HTMLResponse)
def login_page(): return HTMLResponse(LOGIN_HTML)

@app.get("/register", response_class=HTMLResponse)
def register_page(): return HTMLResponse(REGISTER_HTML)

@app.post("/auth/register")
def auth_register(r: AuthRegisterRequest):
    from .auth import has_users
    if has_users(): raise HTTPException(403,"Registration is closed after the first account. An administrator must create additional users.")
    try:
        user=create_account(r.username,r.password,r.display_name)
    except ValueError as exc: raise HTTPException(400,str(exc))
    response=JSONResponse({"user":user})
    response.set_cookie("myai_session",create_session(int(user["id"])),httponly=True,samesite="strict",max_age=86400,path="/")
    return response

@app.post("/auth/login")
def auth_login(r: AuthLoginRequest):
    key=r.username.strip().lower()
    import time
    count,started=_LOGIN_FAILURES.get(key,(0,time.time()))
    if time.time()-started>300: count,started=0,time.time()
    if count>=5: raise HTTPException(429,"Too many failed login attempts. Try again later.")
    user=authenticate(r.username,r.password)
    if not user:
        _LOGIN_FAILURES[key]=(count+1,started)
        raise HTTPException(401,"نام کاربری یا رمز عبور نادرست است.")
    _LOGIN_FAILURES.pop(key,None)
    response=JSONResponse({"user":user})
    response.set_cookie("myai_session",create_session(int(user["id"])),httponly=True,samesite="strict",max_age=86400,path="/")
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
    llm=create_llm()
    def generate():
        stream=getattr(llm,"stream_chat",None)
        if stream is None:
            yield agent.chat(r.message,r.session_id)
            return
        for chunk in stream(r.message):
            yield chunk
    audit(user,"chat","stream","200")
    return StreamingResponse(generate(),media_type="text/plain; charset=utf-8")

@app.get("/memory/knowledge")
def knowledge_list(request: Request, status: str | None = None, limit: int = 200):
    require_user(request)
    limit=max(1,min(limit,1000))
    if status:
        return {"items":fetch_all("SELECT * FROM knowledge WHERE verification_status=? ORDER BY id DESC LIMIT ?",(status,limit))}
    return {"items":fetch_all("SELECT * FROM knowledge ORDER BY id DESC LIMIT ?",(limit,))}

@app.put("/memory/knowledge/{knowledge_id}")
def knowledge_update(knowledge_id:int, r:KnowledgeUpdateRequest, request:Request):
    user=require_admin(request)
    if not fetch_all("SELECT id FROM knowledge WHERE id=?",(knowledge_id,)): raise HTTPException(404,"Knowledge item not found.")
    execute("UPDATE knowledge SET title=?,content=?,topic=?,source_url=?,verification_status='unverified',verified_at=NULL,verified_by=NULL WHERE id=?",(r.title,r.content,r.topic,r.source_url,knowledge_id))
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
    if not fetch_all("SELECT id FROM knowledge WHERE id=?",(knowledge_id,)): raise HTTPException(404,"Knowledge item not found.")
    execute("UPDATE knowledge SET verification_status='verified',verified_at=CURRENT_TIMESTAMP,verified_by=? WHERE id=?",(user["id"],knowledge_id))
    audit(user,"knowledge","verify","200",f"verified:{knowledge_id}")
    return {"verified":knowledge_id}

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
    result=transcribe(r.audio_path,r.model_path,r.language)
    audit(user,"voice","execute","200")
    return {"text":result}

@app.post("/voice/synthesize")
def voice_synthesize(r:VoiceSynthesizeRequest, request:Request):
    user=require_user(request)
    result=synthesize(r.text,r.model_path,r.output_path)
    audit(user,"voice","execute","200")
    return {"path":result}

@app.get("/voice/status")
def voice_status_api(request:Request):
    require_user(request)
    return {**voice_status(), "engine": voice_engine_status()}

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
    path=backup_database(r.path)
    audit(user,"database","backup","200",path)
    return {"path":path}

@app.post("/backup/export")
def backup_export(r:BackupRequest, request:Request):
    user=require_admin(request)
    path=export_database(r.path)
    audit(user,"database","export","200",path)
    return {"path":path}

@app.post("/backup/import")
def backup_import(r:ImportRequest, request:Request):
    user=require_admin(request)
    result=import_database(r.path)
    audit(user,"database","import","200",r.path)
    return {"imported":result}

@app.get("/eval/retrieval")
def eval_retrieval_api(request:Request):
    require_admin(request)
    return eval_retrieval()

@app.get("/self-update/status")
def self_update_status_api(request:Request):
    require_admin(request)
    return self_update_status()

@app.post("/self-update/apply")
def self_update_apply_api(r:ChatRequest, request:Request):
    user=require_admin(request)
    result=self_update_apply(r.message)
    audit(user,"self-update","write","blocked",result.get("reason",""))
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
    user=require_user(request)
    eid=record_evidence(r.skill_id,r.kind,r.passed,r.details)
    audit(user,"skill-engine","execute","200",f"evidence:{r.skill_id}")
    return {"evidence_id":eid}

@app.post("/skills/revalidate")
def skills_revalidate(r:SkillRevalidateRequest, request:Request):
    user=require_user(request)
    result=revalidate(r.skill_id,r.version)
    audit(user,"skill-engine","execute","200",f"revalidate:{r.skill_id}")
    return result

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
def help_ask(r:ChatRequest):
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
    execute("UPDATE help_updates SET status='approved' WHERE id=?",(update_id,))
    return {"status":"approved","update_id":update_id,"message":"The approved help update is now visible in /help."}
@app.post("/help/reject/{update_id}")
def help_reject(update_id:int,request:Request):
    require_admin(request)
    rows=fetch_all("SELECT * FROM help_updates WHERE id=? AND status='pending'",(update_id,))
    if not rows: raise HTTPException(404,"Pending help update not found.")
    execute("UPDATE help_updates SET status='rejected' WHERE id=?",(update_id,)); return {"status":"rejected","update_id":update_id}
@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model,"executor_mode":settings.exec_mode}

@app.post("/chat")
def chat(r:ChatRequest, request:Request):
    user=require_user(request)
    try:
        msg=r.message.strip(); low=msg.lower()
        aliases={"sql server":"SQL Server","sqlserver":"SQL Server","mssql":"SQL Server","mysql":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","آی او اس":"iOS","python":"Python","پایتون":"Python","php":"PHP","c":"C","javascript":"JavaScript","js":"JavaScript","pentest":"Pentest","pen test":"Pentest","penetration testing":"Pentest","penetration test":"Pentest","پنتست":"Pentest","پن تست":"Pentest","تست نفوذ":"Pentest","امنیت":"Pentest"}; requested=next((name for key,name in sorted(aliases.items(),key=lambda x:len(x[0]),reverse=True) if key in low),None)
        learn_intent=("یاد بگیر" in low or "یادگیری" in low or "learn" in low or "go learn" in low or "start learning" in low); sid=r.session_id or execute("INSERT INTO chat_sessions(title,kind,language,user_id) VALUES(?,?,?,?)",(msg[:60] or "گفتگوی جدید","learning" if learn_intent else "chat",requested,user["id"])); policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
        help_intent=("راهنما" in low or "چطور وصل" in low or "چطور استفاده" in low or "how do i" in low or "how to" in low or "setup" in low)
        if help_intent:
            component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
            return {"type":"help","answer":"راهنمای هوشمند آماده شد.","data":ask_help(msg,component,agent.llm,learner.web)}
        code_words=("برنامه بنویس","کد بنویس","برام برنامه","write a program","write code","program","build an app","create an app"); code_intent=any(x in low for x in code_words)
        if security_words:
            if code_intent:
                language=requested or "Python"; generated=learner.generate_program(msg,language); result=learner.security_assessment_code(generated["code"],language,fix_requested); result["generated_project"]=generated; result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"; return {"type":"security","answer":"Security test completed." if not fix_requested else "Security test, remediation and retest completed.","data":result}
            path=None
            for prefix in ("مسیر:","آدرس:","path:","url:","project:","پروژه:"):
                if prefix in msg: path=msg.split(prefix,1)[1].strip().strip('"').strip("'"); break
            if not path:
                m=re.search(r"https?://[^\s]+",msg)
                if m:path=m.group(0).rstrip(".,)")
            if path:
                if path.lower().startswith(("http://","https://")): result=learner.security_assessment_url(path,r.headers if hasattr(r,"headers") else None); result["note"]="External targets are report-only; remediation is not applied remotely."
                else: result=learner.security_assessment_path(path,fix_requested)
                result["mode"]="external_report" if path.lower().startswith(("http://","https://")) else ("pentest_and_fix" if fix_requested else "pentest_report"); return {"type":"security","answer":"Security test completed for the explicitly supplied target.","data":result}
        if learn_intent:
            language=requested or "Python"
            language=canonical_language(language)
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"user",msg))
            scheduler.interval_seconds=3600
            scheduler.start(language)
            answer=f"یادگیری {language} در پس‌زمینه شروع شد."
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"assistant",answer)); execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(sid,))
            return {"type":"learning","answer":answer,"data":{"status":"started","language":language,"interval_seconds":3600,"session_id":sid},"session_id":sid}
        if code_intent:
            language=requested or "Python"
            return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
        if any(x in low for x in ("تأیید آپدیت","تایید آپدیت","confirm update","approve update","apply update")) and user["role"] != "admin":
            raise HTTPException(403,"Self-update requires administrator approval.")
        return {"type":"chat","answer":agent.chat(msg,sid),"session_id":sid}
    except Exception as e: raise HTTPException(502,str(e))

@app.post("/learn/url")
def learn_url(r:URLRequest):
    try:return learner.study_url(str(r.url),r.topic)
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/learning/start")
def learning_start(r:LanguageRequest): return learner.start(r.language)
@app.post("/learning/step")
def learning_step(r:LanguageRequest):
    try:return learner.learn_next(r.language)
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/learning/status")
def learning_status(language:str|None=None): return learner.status(language)
@app.post("/learning/practice")
def practice(r:ChatRequest):
    try:return learner.practice(r.message)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/code/run")
def code_run(r:CodeRequest): return learner.validate_code(r.code)
@app.post("/code/generate")
def code_generate(r:ProgramRequest):
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
            import subprocess
            r=subprocess.run([exe,"auth","logout","--hostname","github.com","--yes"],capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if r.returncode != 0:
                raise RuntimeError((r.stderr or r.stdout or "GitHub logout failed").strip())
        return {"authenticated":False,"message":"از GitHub خارج شدی."}
    except Exception as e:
        raise HTTPException(502,str(e))

@app.get("/git/connection")
def git_connection():
    try:
        data=GitHubConnector().repo("cognitive-kernel/My-ai")
        return {"connected":True,"authenticated":GitHubConnector.token_status(),"repository":data.get("full_name"),"private":data.get("private",False)}
    except Exception as e:
        return {"connected":False,"authenticated":bool(__import__("os").getenv("GITHUB_TOKEN")),"error":str(e)}
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
            repo_data=c.repo("cognitive-kernel/My-ai")
            identity=repo_data.get("owner") or {}
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
        data=c.repo("cognitive-kernel/My-ai")
        identity=data.get("owner") or {}
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
def git_check(repository:str="cognitive-kernel/My-ai"):
    c=GitHubConnector()
    token_source=GitHubConnector.token_source()
    if token_source == "none":
        return {"authenticated":False,"repository":repository,"status":"no_token","message":"GitHub Token تنظیم نشده است."}
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
def git_file(repository:str,path:str,ref:str|None=None): return GitHubConnector().file(repository,path,ref)
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
def project_plan(r:ProjectRequest):
    try:return {"tasks":agent.plan_project(r.goal)}
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/memory/knowledge")
def knowledge(): return fetch_all("SELECT * FROM knowledge ORDER BY id DESC")
@app.get("/memory/search")
def memory_search(q:str,limit:int=8):
    from .memory import recall; return recall(q,limit)
@app.get("/projects/tasks")
def project_tasks(): return fetch_all("SELECT * FROM project_tasks ORDER BY id")
@app.post("/scheduler/start")
def scheduler_start(r:SchedulerRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.get("/scheduler/status")
def scheduler_status(): return scheduler.status()
@app.post("/learning/learn")
def learning_learn(r:LearnRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.post("/scheduler/stop")
def scheduler_stop(): scheduler.stop(); return {"status":"stopped"}
