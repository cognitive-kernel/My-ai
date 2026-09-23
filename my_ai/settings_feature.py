from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.types import Message

from .auth import require_admin, require_user, audit
from .db import execute, fetch_all, init_db
from .git_connector import GitHubConnector
from .llm import create_llm
from .settings_store import get_setting, set_setting, get_bool, get_int, get_github_settings

router = APIRouter(tags=["settings"])
_workers = ThreadPoolExecutor(max_workers=1, thread_name_prefix="myai-learning")
_running: set[int] = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS custom_courses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL DEFAULT '',
 active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS custom_course_topics (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER NOT NULL,
 topic_order INTEGER NOT NULL,
 title TEXT NOT NULL,
 goal TEXT NOT NULL DEFAULT '',
 source_url TEXT,
 FOREIGN KEY(course_id) REFERENCES custom_courses(id) ON DELETE CASCADE,
 UNIQUE(course_id,topic_order)
);
CREATE TABLE IF NOT EXISTS custom_course_progress (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER NOT NULL,
 topic_id INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'planned',
 progress_percent REAL NOT NULL DEFAULT 0,
 phase TEXT NOT NULL DEFAULT 'planned',
 lesson TEXT,
 score REAL,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(course_id,topic_id),
 FOREIGN KEY(course_id) REFERENCES custom_courses(id) ON DELETE CASCADE,
 FOREIGN KEY(topic_id) REFERENCES custom_course_topics(id) ON DELETE CASCADE
);
"""

DEFAULT_TOPICS = [
("Cisco IOS CLI and device management","Privileged EXEC, configuration modes, show commands, interfaces and safe configuration workflow","https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26/products-installation-and-configuration-guides-list.html"),
("IPv4 and IPv6 addressing","Addressing, subnetting, interfaces, gateways and verification commands","https://www.netacad.com/authoring-resources/courses/ff9e491c-49be-4734-803e-a79e6e83dab1/850c6c9b-b788-4915-b7d1-ac915f584548/en-US/assets/IPD%20-%20Shaping%20Future%20Tech%20Careers%20Empowering%20Educators%20with%20Cisco%20Certification-Aligned%20Pathways_en-US_1755107650203.pdf"),
("Switching and VLANs","Ethernet switching, VLAN segmentation, trunking and SVIs","https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26/products-installation-and-configuration-guides-list.html"),
("STP and EtherChannel","Spanning Tree concepts, loop prevention and link aggregation","https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26/products-installation-and-configuration-guides-list.html"),
("Static routing and OSPF","Routing tables, static routes, OSPF concepts, configuration and verification","https://www.cisco.com/c/en/us/td/docs/routers/ios-xe/ip-routing/b-ip-routing/m_iro-mode-ospfv2.html"),
("NAT and PAT","Inside/outside roles, static and dynamic NAT and PAT","https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipaddr_nat/configuration/xe-2/nat-xe-2-book/iadnat-addr-consv.html"),
("IPv4 and IPv6 ACLs","Standard and extended ACLs, wildcard masks and interface application","https://www.cisco.com/c/en/us/td/docs/routers/ios-xe/security-vpn/security-vpn/m_sec-create-ip-apply-0.html"),
("WAN, VPN and IPsec","WAN connectivity, VPN concepts and IPsec foundations","https://www.netacad.com/courses/ccna-enterprise-networking-security-automation"),
("Network management","CDP, LLDP, NTP, SNMP, Syslog and device file maintenance","https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26/products-installation-and-configuration-guides-list.html"),
("QoS and traffic handling","Traffic characteristics, queuing concepts and QoS implementation","https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe-26/products-installation-and-configuration-guides-list.html"),
("Network automation","REST APIs, data formats, programmability and configuration automation","https://www.netacad.com/courses/ccna-enterprise-networking-security-automation"),
("Troubleshooting and capstone","Evidence-driven troubleshooting, documentation, verification and a complete lab","https://www.netacad.com/courses/ccna-enterprise-networking-security-automation"),
]

class CourseRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    topics: list[dict[str, str]] = Field(min_length=1, max_length=100)

class TokenRequest(BaseModel):
    token: str = Field(default="", max_length=10000)

class GithubConfigRequest(BaseModel):
    api_url: str = Field(min_length=8, max_length=500)
    repository: str = Field(min_length=3, max_length=300)
    username: str = Field(default="", max_length=200)

class FeatureSettingsRequest(BaseModel):
    self_update_enabled: bool = False
    self_update_approved: bool = False
    self_update_health_url: str = ""
    self_repair_enabled: bool = True
    self_repair_require_approval: bool = True
    learning_fast_enabled: bool = False
    learning_interval_seconds: int = 3600
    learning_max_retries: int = 5

class ToolPermissionRequest(BaseModel):
    user_id: int
    tool_name: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=40)
    allowed: bool

class ResourceSettingsRequest(BaseModel):
    cpu_percent: float = 70.0
    cpu_threads: int = 8
    ram_percent: float = 80.0
    gpu_layers: int = 0


def _setup() -> None:
    init_db()
    from .db import connect
    with connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",)).fetchone()
        if not row:
            cur = conn.execute("INSERT INTO custom_courses(name,description) VALUES(?,?)", ("Cisco", "Cisco networking / IOS learning path with practical, verification-focused modules."))
            if cur.lastrowid is None:
                raise RuntimeError("Unable to create the default Cisco course")
            course_id = int(cur.lastrowid)
            for order, (title, goal, source) in enumerate(DEFAULT_TOPICS, 1):
                tcur = conn.execute("INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)", (course_id, order, title, goal, source))
                if tcur.lastrowid is None:
                    raise RuntimeError("Unable to create a Cisco topic")
                conn.execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, int(tcur.lastrowid)))
        conn.commit()


def _course(course_id: int) -> dict[str, Any] | None:
    rows = fetch_all("SELECT * FROM custom_courses WHERE id=?", (course_id,))
    return rows[0] if rows else None


def _progress(course_id: int) -> list[dict[str, Any]]:
    return fetch_all("""SELECT t.id,t.topic_order,t.title,t.goal,t.source_url,
        COALESCE(p.status,'planned') status,COALESCE(p.progress_percent,0) progress_percent,
        COALESCE(p.phase,'planned') phase,p.lesson,p.score,p.updated_at
        FROM custom_course_topics t LEFT JOIN custom_course_progress p ON p.topic_id=t.id
        WHERE t.course_id=? ORDER BY t.topic_order""", (course_id,))


def _summary(course_id: int) -> dict[str, Any]:
    items = _progress(course_id)
    completed = sum(1 for x in items if x["status"] == "completed")
    current = next((x for x in items if x["status"] == "started"), None)
    if current is None:
        current = next((x for x in items if x["status"] != "completed"), None)
    overall = round(((completed + (float(current["progress_percent"]) / 100 if current else 0)) / len(items) * 100), 1) if items else 0
    return {"course_id": course_id, "total_topics": len(items), "completed_topics": completed, "progress_percent": overall, "current": current, "topics": items}


def _set_topic(topic_id: int, status: str, progress: float, phase: str, lesson: str | None = None, score: float | None = None) -> None:
    execute("UPDATE custom_course_progress SET status=?,progress_percent=?,phase=?,lesson=COALESCE(?,lesson),score=COALESCE(?,score),updated_at=CURRENT_TIMESTAMP WHERE topic_id=?", (status, max(0,min(100,float(progress))), phase, lesson, score, topic_id))


def _learn_topic(course_id: int, topic: dict[str, Any]) -> None:
    topic_id = int(topic["id"])
    _set_topic(topic_id, "started", 5, "understanding")
    llm = create_llm("general")
    prompt = ("Teach this study unit accurately and practically. Explain prerequisites, concepts, Cisco IOS/IOS XE command examples, verification commands, common mistakes, safe lab exercises, and a short mastery checklist. "
              "Do not claim a command is valid for every Cisco platform/version; state platform/version uncertainty. Prefer official Cisco documentation when supplied.\n"
              f"COURSE: Cisco\nTOPIC: {topic['title']}\nGOAL: {topic['goal']}\nOFFICIAL SOURCE: {topic.get('source_url') or 'none'}")
    _set_topic(topic_id, "started", 25, "lesson")
    lesson = llm.chat(prompt, system="You are a rigorous Cisco networking instructor. Return a concise but technically precise lesson.")
    _set_topic(topic_id, "started", 70, "assessment", lesson=lesson)
    raw = llm.chat("Return only a numeric score from 0 to 100 for whether this lesson adequately covers the stated goal. GOAL:" + topic["goal"] + "\nLESSON:" + lesson)
    match = re.search(r"(?<!\d)(100|\d{1,2})(?!\d)", raw)
    score = float(match.group(1)) if match else 0.0
    _set_topic(topic_id, "completed", 100, "completed", score=score)
    audit(None, "learning", "execute", "200", f"custom-course:{course_id}:topic:{topic_id}")


def _run_course(course_id: int) -> None:
    if course_id in _running:
        return
    _running.add(course_id)
    try:
        while True:
            course = _course(course_id)
            if not course or not course["active"]:
                return
            rows = _progress(course_id)
            topic = next((x for x in rows if x["status"] not in {"completed", "paused"}), None)
            if not topic:
                return
            try:
                _learn_topic(course_id, topic)
            except Exception as exc:
                _set_topic(int(topic["id"]), "paused", max(5, float(topic["progress_percent"])), "error", lesson=f"Learning paused after an error: {exc}")
                return
            if not fetch_all("SELECT id FROM custom_course_topics t WHERE t.course_id=? AND NOT EXISTS (SELECT 1 FROM custom_course_progress p WHERE p.topic_id=t.id AND p.status='completed')", (course_id,)):
                return
    finally:
        _running.discard(course_id)


@router.get("/settings/config")
def settings_config(request: Request):
    require_admin(request)
    g=get_github_settings()
    return {
        "github": {"api_url":g.get("api_url",""),"repository":g.get("repository",""),"username":g.get("username",""),"token_configured":bool(g.get("token"))},
        "features": {
            "self_update_enabled":get_bool("self_update.enabled",False),
            "self_update_approved":get_bool("self_update.approved",False),
            "self_update_health_url":str(get_setting("self_update.health_url","")),
            "self_repair_enabled":get_bool("self_repair.enabled",True),
            "self_repair_require_approval":get_bool("self_repair.require_approval",True),
            "learning_fast_enabled":get_bool("learning.fast_enabled",False),
            "learning_interval_seconds":get_int("learning.interval_seconds",3600),
            "learning_max_retries":get_int("learning.max_retries",5),
        },
        "resources": {
            "cpu_percent": float(get_setting("resources.cpu_percent", "70")),
            "cpu_threads": get_int("resources.cpu_threads", 8),
            "ram_percent": float(get_setting("resources.ram_percent", "80")),
            "gpu_layers": get_int("resources.gpu_layers", 0),
        },
    }

@router.put("/settings/github")
def save_github_config(r: GithubConfigRequest, request: Request):
    user=require_admin(request)
    try:
        GitHubConnector.save_config(api_url=r.api_url,repository=r.repository,username=r.username)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    audit(user,"github","write","200","settings-configured")
    return {"saved":True}

@router.put("/settings/features")
def save_feature_settings(r: FeatureSettingsRequest, request: Request):
    user=require_admin(request)
    if not 60 <= r.learning_interval_seconds <= 86400:
        raise HTTPException(400,"learning_interval_seconds must be 60..86400")
    if not 1 <= r.learning_max_retries <= 20:
        raise HTTPException(400,"learning_max_retries must be 1..20")
    if r.self_update_health_url:
        from urllib.parse import urlparse
        host=urlparse(r.self_update_health_url).hostname
        if host not in {"127.0.0.1","localhost","::1"}:
            raise HTTPException(400,"Self-update health URL must target the local host.")
    values={"self_update.enabled":r.self_update_enabled,"self_update.approved":r.self_update_approved,"self_update.health_url":r.self_update_health_url.strip(),"self_repair.enabled":r.self_repair_enabled,"self_repair.require_approval":r.self_repair_require_approval,"learning.fast_enabled":r.learning_fast_enabled,"learning.interval_seconds":r.learning_interval_seconds,"learning.max_retries":r.learning_max_retries}
    for key,value in values.items(): set_setting(key,value)
    audit(user,"settings","write","200","feature-settings-updated")
    return {"saved":True,"features":values}

@router.put("/settings/resources")
def save_resource_settings(r: ResourceSettingsRequest, request: Request):
    user = require_admin(request)
    if not 1 <= r.cpu_percent <= 100:
        raise HTTPException(400, "cpu_percent must be 1..100")
    if not 1 <= r.cpu_threads <= 128:
        raise HTTPException(400, "cpu_threads must be 1..128")
    if not 1 <= r.ram_percent <= 100:
        raise HTTPException(400, "ram_percent must be 1..100")
    if not 0 <= r.gpu_layers <= 128:
        raise HTTPException(400, "gpu_layers must be 0..128")
    set_setting("resources.cpu_percent", round(r.cpu_percent, 2))
    set_setting("resources.cpu_threads", r.cpu_threads)
    set_setting("resources.ram_percent", round(r.ram_percent, 2))
    set_setting("resources.gpu_layers", r.gpu_layers)
    audit(user, "settings", "write", "200", "resource-settings-updated")
    return {"saved": True, "resources": {"cpu_percent": r.cpu_percent, "cpu_threads": r.cpu_threads, "ram_percent": r.ram_percent, "gpu_layers": r.gpu_layers}}

@router.get("/settings/users")
def settings_users(request: Request):
    require_admin(request)
    return {"items": fetch_all("SELECT id,username,display_name,role,active,created_at FROM users ORDER BY id")}

@router.get("/settings/tool-permissions")
def settings_tool_permissions(request: Request):
    require_admin(request)
    return {"items":fetch_all("SELECT * FROM tool_permissions ORDER BY user_id,tool_name,action")}

@router.put("/settings/tool-permissions")
def save_tool_permission(r: ToolPermissionRequest, request: Request):
    user=require_admin(request)
    if not fetch_all("SELECT id FROM users WHERE id=?",(r.user_id,)):
        raise HTTPException(404,"User not found.")
    execute("""INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,?)
              ON CONFLICT(user_id,tool_name,action) DO UPDATE SET allowed=excluded.allowed,updated_at=CURRENT_TIMESTAMP""",(r.user_id,r.tool_name,r.action,1 if r.allowed else 0))
    audit(user,"tool-permissions","write","200",f"{r.user_id}:{r.tool_name}:{r.action}:{r.allowed}")
    return {"ok":True}

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    require_admin(request)
    return HTMLResponse(SETTINGS_HTML)

@router.get("/learning", response_class=HTMLResponse)
def learning_page(request: Request):
    require_user(request)
    return HTMLResponse(LEARNING_HTML)

@router.get("/settings/courses")
def courses(request: Request):
    require_admin(request)
    _setup()
    out=[]
    for c in fetch_all("SELECT * FROM custom_courses ORDER BY id"):
        s=_summary(int(c["id"])); c.update({"progress_percent":s["progress_percent"],"completed_topics":s["completed_topics"],"total_topics":s["total_topics"],"current":s["current"]}); out.append(c)
    return {"items":out}

@router.post("/settings/courses")
def create_course(r: CourseRequest, request: Request):
    user=require_admin(request); _setup()
    name=r.name.strip()
    if not name: raise HTTPException(400,"Course name is required.")
    try: cid=execute("INSERT INTO custom_courses(name,description) VALUES(?,?)",(name,r.description.strip()))
    except Exception as exc: raise HTTPException(400,"Course name already exists.") from exc
    for order,item in enumerate(r.topics,1):
        title=str(item.get("title","")).strip(); goal=str(item.get("goal","")).strip(); source=(str(item.get("source_url","")).strip() or None)
        if not title: raise HTTPException(400,"Every course topic needs a title.")
        tid=execute("INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",(cid,order,title,goal,source))
        execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)",(cid,tid))
    audit(user,"learning","write","200",f"course-created:{cid}")
    return {"id":cid,"status":"created"}

@router.get("/settings/courses/{course_id}/progress")
def course_progress(course_id:int,request:Request):
    require_user(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    return _summary(course_id)

@router.post("/settings/courses/{course_id}/start")
def course_start(course_id:int,request:Request):
    user=require_user(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    if course_id not in _running:
        _workers.submit(_run_course,course_id)
    audit(user,"learning","execute","202",f"course-start:{course_id}")
    return {"status":"started","course_id":course_id}

@router.post("/settings/courses/{course_id}/pause")
def course_pause(course_id:int,request:Request):
    user=require_admin(request); _setup()
    execute("UPDATE custom_course_progress SET status='paused',phase='paused',updated_at=CURRENT_TIMESTAMP WHERE course_id=? AND status='started'",(course_id,))
    audit(user,"learning","write","200",f"course-pause:{course_id}")
    return {"status":"paused","course_id":course_id}

@router.post("/settings/github-token")
def github_token(r:TokenRequest,request:Request):
    user=require_admin(request)
    token=r.token.strip()
    if token and len(token)<20: raise HTTPException(400,"GitHub token is too short.")
    try:
        if not token:
            GitHubConnector.save_token("")
            return {"saved":False,"authenticated":False}
        GitHubConnector.save_token(token)
        identity=GitHubConnector(token=token).whoami()
        audit(user,"github","write","200",f"token-saved:{identity.get('login','unknown')}")
        return {"saved":True,"authenticated":True,"login":identity.get("login"),"name":identity.get("name")}
    except Exception as exc:
        GitHubConnector.save_token("")
        raise HTTPException(502,f"GitHub token verification failed: {exc}") from exc

@router.get("/settings/github")
def github_settings(request:Request):
    require_admin(request)
    try:
        return {"connection":GitHubConnector().whoami(),"token_source":GitHubConnector.token_source()}
    except Exception as exc:
        return {"connection":None,"token_source":GitHubConnector.token_source(),"error":str(exc)}

@router.get("/learning/active")
def learning_active(request:Request):
    require_user(request); _setup()
    items=[]
    for c in fetch_all("SELECT * FROM custom_courses WHERE active=1 ORDER BY id"):
        summary=_summary(int(c["id"]))
        items.append({"course":c,"summary":summary,"active":summary["completed_topics"] < summary["total_topics"]})
    return {"items":items,"running":sorted(_running)}

@router.get("/learning/catalog")
def learning_catalog(request:Request):
    require_user(request); _setup()
    return {"items":fetch_all("SELECT * FROM custom_courses WHERE active=1 ORDER BY id")}

@router.post("/learning/{course_id}/start")
def learning_start_public(course_id:int,request:Request):
    return course_start(course_id,request)

SETTINGS_JS = '''function byId(id){return document.getElementById(id)}
async function req(url,opt){var r=await fetch(url,opt||{});var text=await r.text();var j={};try{j=JSON.parse(text)}catch(e){throw Error('پاسخ نامعتبر از سرور (HTTP '+r.status+')')}if(!r.ok)throw Error(j.detail||j.message||('HTTP '+r.status));return j}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function setText(id,value){var e=byId(id);if(e)e.textContent=value}
async function loadUsers(){var box=byId('users');if(!box)return;box.textContent='در حال بارگذاری...';try{var j=await req('/settings/users');var items=j.items||[];box.innerHTML=items.map(function(u){return '<div class="topic"><b>'+esc(u.username)+'</b> — '+esc(u.display_name||'بدون نام')+' — نقش: '+esc(u.role)+' — '+(u.active?'فعال':'غیرفعال')+(u.role==='admin'?'':' <button type="button" onclick="toggleUser('+u.id+','+(!u.active)+')">'+(u.active?'غیرفعال‌کردن':'فعال‌کردن')+'</button>')+'</div>'}).join('')||'کاربری ثبت نشده است'}catch(e){box.textContent='خطا در بارگذاری کاربران: '+e.message}}
async function toggleUser(id,active){try{await req('/admin/users/'+id+'/active?active='+active,{method:'PATCH'});await loadUsers()}catch(e){setText('userout',e.message)}}
async function addUser(){try{var j=await req('/admin/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:byId('nu').value,password:byId('np').value,display_name:byId('nd').value,active:true})});setText('userout','کاربر ایجاد شد: '+j.user.username);byId('nu').value='';byId('np').value='';byId('nd').value='';loadUsers();loadPermissions()}catch(e){setText('userout',e.message)}}
async function loadSettings(){try{var j=await req('/settings/config');byId('apiurl').value=j.github.api_url||'';byId('repo').value=j.github.repository||'';byId('ghuser').value=j.github.username||'';byId('su_enabled').checked=!!j.features.self_update_enabled;byId('su_approved').checked=!!j.features.self_update_approved;byId('su_health').value=j.features.self_update_health_url||'';byId('sr_enabled').checked=!!j.features.self_repair_enabled;byId('sr_approval').checked=!!j.features.self_repair_require_approval;byId('lf_enabled').checked=!!j.features.learning_fast_enabled;byId('lf_interval').value=j.features.learning_interval_seconds;byId('lf_retries').value=j.features.learning_max_retries;byId('cpu_percent').value=j.resources.cpu_percent;byId('cpu_threads').value=j.resources.cpu_threads;byId('ram_percent').value=j.resources.ram_percent;byId('gpu_layers').value=j.resources.gpu_layers;setText('gitout',j.github.token_configured?'Token تنظیم شده است':'Token تنظیم نشده است');setText('resourceout','مقادیر فعال: CPU '+j.resources.cpu_percent+'% · '+j.resources.cpu_threads+' thread · RAM '+j.resources.ram_percent+'% · GPU '+j.resources.gpu_layers+' layer')}catch(e){setText('gitout','خطا در بارگذاری تنظیمات: '+e.message)}}
async function saveGithubConfig(){try{await req('/settings/github',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_url:byId('apiurl').value.trim(),repository:byId('repo').value.trim(),username:byId('ghuser').value.trim()})});setText('gitout','تنظیمات GitHub ذخیره شد')}catch(e){setText('gitout',e.message)}}
async function saveToken(){try{var j=await req('/settings/github-token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:byId('token').value})});setText('gitout',j.authenticated?'Token معتبر و متصل به @'+j.login:'Token حذف شد');byId('token').value='';loadSettings()}catch(e){setText('gitout',e.message)}}
async function checkGit(){try{var j=await req('/git/check');setText('gitout',j.message||j.status||'بررسی انجام شد')}catch(e){setText('gitout','خطا در بررسی اتصال: '+e.message)}}
async function saveFeatures(){try{await req('/settings/features',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({self_update_enabled:byId('su_enabled').checked,self_update_approved:byId('su_approved').checked,self_update_health_url:byId('su_health').value,self_repair_enabled:byId('sr_enabled').checked,self_repair_require_approval:byId('sr_approval').checked,learning_fast_enabled:byId('lf_enabled').checked,learning_interval_seconds:Number(byId('lf_interval').value||3600),learning_max_retries:Number(byId('lf_retries').value||5)})});setText('suout','تنظیمات ذخیره شد');setText('srout','تنظیمات ذخیره شد');setText('lfout','تنظیمات ذخیره شد');loadSettings()}catch(e){setText('suout',e.message);setText('srout',e.message);setText('lfout',e.message)}}
window.saveResources=window.saveResources=async function saveResources(){try{var payload={cpu_percent:Number(byId('cpu_percent').value||70),cpu_threads:Number(byId('cpu_threads').value||8),ram_percent:Number(byId('ram_percent').value||80),gpu_layers:Number(byId('gpu_layers').value||0)};var j=await req('/settings/resources',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});byId('cpu_percent').value=j.resources.cpu_percent;byId('cpu_threads').value=j.resources.cpu_threads;byId('ram_percent').value=j.resources.ram_percent;byId('gpu_layers').value=j.resources.gpu_layers;setText('resourceout','مقادیر فعال: CPU '+j.resources.cpu_percent+'% · '+j.resources.cpu_threads+' thread · RAM '+j.resources.ram_percent+'% · GPU '+j.resources.gpu_layers+' layer')}catch(e){setText('resourceout','خطا در ذخیره منابع: '+e.message)}}
var PERM_TOOLS=['chat','code-generation','code-execution','learning','scheduler','github','security','database','voice','models','memory','web','projects','eval','self-update','self-repair','help','tools'];
function permissionCell(uid,tool,action,allowed){return '<label style="display:inline-block;margin:3px"><input type="checkbox" '+(allowed?'checked':'')+' onchange="setPermission('+uid+',\''+tool+'\',\''+action+'\',this.checked)"> '+tool+':'+action+'</label>'}
async function loadPermissions(){var box=byId('permissions');if(!box)return;box.textContent='در حال بارگذاری...';try{var pair=await Promise.all([req('/settings/users'),req('/settings/tool-permissions')]);var usersList=pair[0].items||[];var items=pair[1].items||[];var map={};items.forEach(function(x){map[x.user_id+':'+x.tool_name+':'+x.action]=!!x.allowed});box.innerHTML=usersList.map(function(user){var html='<div class="topic"><b>'+esc(user.username)+'</b> — '+esc(user.role)+'<div>';PERM_TOOLS.forEach(function(tool){['read','write','execute'].forEach(function(action){html+=permissionCell(user.id,tool,action,!!map[user.id+':'+tool+':'+action])})});return html+'</div></div>'}).join('')||'کاربری ثبت نشده است'}catch(e){box.textContent='خطا در بارگذاری مجوزها: '+e.message}}
async function setPermission(uid,tool,action,allowed){try{await req('/settings/tool-permissions',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,tool_name:tool,action:action,allowed:allowed})})}catch(e){alert('خطا در ذخیره مجوز: '+e.message);loadPermissions()}}
async function loginGit(){try{var j=await req('/git/login',{method:'POST'});setText('gitout',j.message||'درخواست ورود ارسال شد')}catch(e){setText('gitout',e.message)}}
async function logoutGit(){try{var j=await req('/git/logout',{method:'POST'});setText('gitout',j.message||'خروج انجام شد');loadSettings()}catch(e){setText('gitout',e.message)}}
async function createCourse(){try{var lines=byId('ct').value.split(/\n+/).map(function(x){return x.trim()}).filter(Boolean);var topics=lines.map(function(x){var p=x.split('|').map(function(v){return v.trim()});return {title:p[0],goal:p[1]||'',source_url:p[2]||''}});var j=await req('/settings/courses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:byId('cn').value,description:byId('cd').value,topics:topics})});setText('courseout','آموزش ساخته شد: '+j.id);loadCourses()}catch(e){setText('courseout',e.message)}}
async function startCourse(id){try{await req('/settings/courses/'+id+'/start',{method:'POST'});loadCourses()}catch(e){setText('courseout',e.message)}}
async function loadCourses(){var box=byId('courses');if(!box)return;try{var j=await req('/settings/courses');box.innerHTML=(j.items||[]).map(function(c){return '<div class="card"><h3>'+esc(c.name)+'</h3><p>'+esc(c.description)+'</p><div class="bar"><div class="fill" style="width:'+c.progress_percent+'%">'+c.progress_percent+'%</div></div><p class="muted">'+c.completed_topics+' از '+c.total_topics+' سرفصل کامل شده'+(c.current?' · اکنون: '+esc(c.current.title)+' · مرحله: '+esc(c.current.phase):'')+'</p><button type="button" onclick="startCourse('+c.id+')">شروع/ادامه یادگیری</button></div>'}).join('')||'آموزشی نیست'}catch(e){box.textContent='خطا در بارگذاری آموزش‌ها: '+e.message}}
loadSettings();loadUsers();loadPermissions();loadCourses();setInterval(loadCourses,10000)'''\n\nSETTINGS_HTML = """<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>تنظیمات | My-AI</title><style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0;color:#17202a}.wrap{max-width:1100px;margin:auto;padding:20px}.card{background:#fff;padding:18px;border-radius:14px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}input,textarea,select{width:100%;box-sizing:border-box;padding:10px;margin:5px 0;border:1px solid #ccc;border-radius:8px}button{padding:9px 14px;margin:3px;border:0;border-radius:8px;cursor:pointer}.bar{height:22px;background:#ddd;border-radius:8px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:22px;font-size:12px}.topic{border:1px solid #ddd;padding:9px;border-radius:9px;margin:6px 0}.muted{font-size:13px;color:#667085}.ok{background:#dcfce7}.warn{background:#fef3c7}.danger{background:#fee2e2}</style><div class='wrap'><form id='settings-form' hidden></form><h1>تنظیمات My-AI</h1><p><a href='/'>صفحه اصلی</a> · <a href='/learning'>پیشرفت و مسیر یادگیری</a></p><div class='grid'><section class='card'><h2>اتصال GitHub</h2><p class='muted'>هیچ Repository یا API URL پیش‌فرضی وجود ندارد. تنظیمات در دیتابیس نگهداری می‌شود؛ Token به‌صورت رمزنگاری‌شده ذخیره می‌شود. GitHub REST API با username/password احراز هویت نمی‌کند و برای API باید Token یا OAuth/CLI استفاده شود.</p><input id='apiurl' placeholder='GitHub API URL'><input id='repo' placeholder='owner/repository'><input id='ghuser' placeholder='GitHub username (اختیاری)'><input id='token' type='password' form='settings-form' autocomplete='new-password' placeholder='Personal Access Token'><button onclick='saveGithubConfig()'>ثبت تنظیمات GitHub</button><button onclick='saveToken()'>ثبت Token</button><button onclick='checkGit()'>بررسی اتصال</button><button onclick='loginGit()'>ورود با GitHub CLI/OAuth</button><button onclick='logoutGit()'>خروج</button><div id='gitout' class='muted'></div></section>
<section class='card'><h2>Self-Update</h2><label><input id='su_enabled' type='checkbox'> فعال‌سازی Self-Update برای بررسی و اجرای به‌روزرسانی خودکار</label><label><input id='su_approved' type='checkbox'> اجازه اجرای Update بدون تأیید دستی در مرحله اجرا</label><input id='su_health' placeholder='Health URL محلی، مثلاً http://127.0.0.1:8000/health'><button onclick='saveFeatures()'>ذخیره</button><div id='suout' class='muted'></div></section>
<section class='card'><h2>Self-Repair</h2><label><input id='sr_enabled' type='checkbox'> فعال‌سازی Self-Repair برای پیشنهاد/اجرای تعمیرات</label><label><input id='sr_approval' type='checkbox' checked> قبل از اعمال تعمیر، تأیید ادمین الزامی باشد</label><button onclick='saveFeatures()'>ذخیره</button><div id='srout' class='muted'></div></section>
<section class='card'><h2>یادگیری سریع</h2><label><input id='lf_enabled' type='checkbox'> فعال</label><input id='lf_interval' type='number' min='60' max='86400' placeholder='فاصله یادگیری (ثانیه)'><input id='lf_retries' type='number' min='1' max='20' placeholder='حداکثر تلاش منبع'><button onclick='saveFeatures()'>ذخیره</button><div id='lfout' class='muted'></div></section><section class='card'><h2>منابع سخت‌افزاری</h2><p class='muted'>سقف پیش‌فرض اجرای یادگیری: CPU برابر 70٪ با 8 thread، RAM برابر 80٪ و GPU برابر 0 لایه (فقط CPU). این مقادیر قابل تغییر هستند.</p><label>حداکثر CPU (%)<input id='cpu_percent' type='number' min='1' max='100' step='0.5'></label><label>تعداد CPU thread<input id='cpu_threads' type='number' min='1' max='128' step='1'></label><label>حداکثر RAM (%)<input id='ram_percent' type='number' min='1' max='100' step='0.5'></label><label>GPU layers (0 = فقط CPU)<input id='gpu_layers' type='number' min='0' max='128' step='1'></label><button onclick='saveResources()'>ذخیره منابع</button><div id='resourceout' class='muted'></div></section><section class='card'><h2>مدیریت کاربران</h2><div id='users'>در حال بارگذاری...</div><hr><input id='nu' placeholder='نام کاربری'><input id='np' type='password' form='settings-form' placeholder='رمز عبور حداقل ۱۰ کاراکتر'><input id='nd' placeholder='نام نمایشی'><button onclick='addUser()'>ایجاد کاربر</button><div id='userout' class='muted'></div></section></div>
<section class='card'><h2>مجوز ابزار کاربران</h2><p class='muted'>برای هر کاربر، ابزار و نوع عملیات را مشخص کنید. عدم وجود مجوز یعنی Deny.</p><div id='permissions'>در حال بارگذاری...</div></section><section class='card'><h2>ساخت آموزش جدید</h2><p class='muted'>هر خط یک سرفصل: <code>عنوان | هدف | آدرس منبع رسمی اختیاری</code>. می‌توانی «Cisco» یا هر موضوع دیگری بسازی.</p><input id='cn' placeholder='نام آموزش، مثلاً Cisco'><input id='cd' placeholder='توضیح آموزش'><textarea id='ct' rows='12' placeholder='Cisco IOS CLI | کار با حالت‌های CLI و show/configure | https://www.cisco.com/...\nVLAN | ساخت VLAN و trunk | https://www.cisco.com/...'></textarea><button onclick='createCourse()'>ایجاد آموزش</button><div id='courseout' class='muted'></div></section><section class='card'><h2>آموزش‌ها و پیشرفت</h2><div id='courses'>در حال بارگذاری...</div></section></div><script src='/settings/script.js?v=20260923-2'></script></html>"""

LEARNING_HTML = """<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>پیشرفت یادگیری | My-AI</title><style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0}.wrap{max-width:1100px;margin:auto;padding:20px}.card{background:#fff;padding:18px;border-radius:14px;margin:12px 0}.bar{height:26px;background:#ddd;border-radius:9px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:26px;min-width:2em}.course{border:1px solid #d0d5dd;border-radius:12px;margin:12px 0;overflow:hidden;background:#fff}.course>summary{cursor:pointer;padding:16px;font-size:18px;font-weight:700;list-style:none}.course>summary::-webkit-details-marker{display:none}.courseBody{padding:0 16px 16px}.topic{padding:12px;border:1px solid #e4e7ec;border-radius:10px;margin:8px 0}.topicHead{display:flex;justify-content:space-between;gap:12px;align-items:center}.started{background:#eff6ff}.completed{background:#ecfdf3}.paused{background:#fffaeb}.small{font-size:13px;color:#667085}pre{direction:ltr;text-align:left}.empty{padding:20px;text-align:center;color:#667085}</style><div class='wrap'><h1>پیشرفت کامل یادگیری</h1><p><a href='/settings'>تنظیمات</a> · <a href='/'>صفحه اصلی</a></p><p class='small'>همه مباحث موجود اینجا هستند. روی هر مبحث کلیک کنید تا سرفصل‌ها و درصد یادگیری هر سرفصل باز شود.</p><div id='root'>در حال بارگذاری...</div></div><script>
async function req(u){let r=await fetch(u,{cache:'no-store'});let j=await r.json();if(!r.ok)throw Error(j.detail||'خطا');return j}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function bar(p){p=Number(p||0);return '<div class="bar"><div class="fill" style="width:'+Math.max(0,Math.min(100,p))+'%">'+p+'%</div></div>'}
function topicHtml(t){var cls=t.status==='completed'?'completed':t.status==='paused'?'paused':t.status==='started'?'started':'';return '<div class="topic '+cls+'"><div class="topicHead"><b>'+esc(t.order||t.topic_order)+'. '+esc(t.topic||t.title)+'</b><b>'+Number(t.progress_percent||0)+'%</b></div>'+bar(t.progress_percent)+'<div class="small">وضعیت: '+esc(t.status)+' · مرحله: '+esc(t.phase)+'</div><div>هدف: '+esc(t.goal)+'</div>'+(t.score!=null?'<div class="small">امتیاز ارزیابی: '+esc(t.score)+'</div>':'')+(t.lesson?'<details><summary>متن درس</summary><pre>'+esc(t.lesson)+'</pre></details>':'')+'</div>'}
async function load(){try{var a=await req('/learning/status'),j=a.courses||[],custom=await req('/learning/active'),html='';j.forEach(function(c){html+='<details class="course"><summary>'+esc(c.language)+' — '+Number(c.progress_percent||0)+'% ('+c.completed_topics+'/'+c.total_topics+')</summary><div class="courseBody">'+bar(c.progress_percent)+c.topics.map(topicHtml).join('')+'</div></details>'});(custom.items||[]).forEach(function(x){var c=x.course,s=x.summary;html+='<details class="course"><summary>'+esc(c.name)+' — '+Number(s.progress_percent||0)+'% ('+s.completed_topics+'/'+s.total_topics+')</summary><div class="courseBody">'+bar(s.progress_percent)+s.topics.map(topicHtml).join('')+'</div></details>'});root.innerHTML=html||'<div class="card empty">هنوز مبحثی ثبت نشده است.</div>'}catch(e){root.textContent='خطا: '+e.message}}
load();setInterval(load,5000)
</script></html>