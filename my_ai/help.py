from __future__ import annotations
import json
from pathlib import Path
from html import escape
from .db import execute, fetch_all
from .access_policy import assert_mutation_allowed


DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "help"
DOC_FILES = {"chat":"chat.md","learning":"learning.md","coding":"coding.md","security":"../SECURITY.md","git":"github.md","memory":"memory.md","scheduler":"scheduler.md","voice":"voice.md","api":"api.md","docker":"docker.md","network-policy":"network-policy.md","self-development":"self-development.md"}
DOC_TITLES = {"chat":"چت و گفتگو","learning":"یادگیری","coding":"برنامه‌نویسی","security":"امنیت و پن‌تست","git":"Git / GitHub","memory":"حافظه","scheduler":"Scheduler","voice":"صدا","api":"API","docker":"Docker","network-policy":"سیاست آفلاین و شبکه","self-development":"خودپایش و توسعه خودکار"}
def local_help(component):
    key=(component or "chat").lower().strip()
    p=DOCS_DIR/DOC_FILES.get(key,"chat.md")
    return p.read_text(encoding="utf-8") if p.exists() else ""
def local_help_html(component):
    out=[]
    for line in local_help(component).splitlines():
        if line.startswith("# "): out.append("<h2>"+escape(line[2:])+"</h2>")
        elif line.startswith("## "): out.append("<h3>"+escape(line[3:])+"</h3>")
        elif line.startswith("- "): out.append("<li>"+escape(line[2:])+"</li>")
        elif line.strip(): out.append("<p>"+escape(line)+"</p>")
    return "".join(out)
def apply_help_update(component, proposal):
    assert_mutation_allowed("help update")
    key=(component or "").lower().strip()
    if key not in DOC_FILES: return False
    p=DOCS_DIR/DOC_FILES[key]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(proposal.strip()+"\n",encoding="utf-8")
    return True

HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>My-AI — راهنما</title>
<style>
body{font-family:Tahoma,system-ui;line-height:1.9;margin:0;background:#f3f4f6;color:#17202a}
main{max-width:1050px;margin:auto;padding:24px}.card{background:#fff;padding:22px;border-radius:14px;margin:14px 0;box-shadow:0 1px 4px #0001}
h1{margin-top:0}h2{border-bottom:1px solid #ddd;padding-bottom:8px}
code,pre{direction:ltr;text-align:left}.cmd{background:#111827;color:#fff;padding:12px;border-radius:8px;overflow:auto}
.tip{background:#eff6ff;padding:12px;border-radius:8px}.warn{background:#fff7ed;padding:12px;border-radius:8px}
a{color:#2563eb}nav{position:sticky;top:0;background:#fff;padding:10px;border-bottom:1px solid #ddd;z-index:2}
nav a{margin:4px;display:inline-block}
 .hero{background:linear-gradient(135deg,#111827,#1e3a8a);color:#fff;padding:24px;border-radius:20px;margin-bottom:16px;box-shadow:0 14px 35px #1e3a8a22}.card{border:1px solid #e5e7eb;box-shadow:0 8px 24px #0f172a0b;transition:.18s}.card:hover{box-shadow:0 12px 30px #0f172a12}nav{border-radius:12px;box-shadow:0 4px 16px #0f172a0a}button{background:#1d4ed8;color:#fff;border:0;border-radius:9px;padding:9px 14px;font-weight:700;cursor:pointer}button:hover{filter:brightness(1.05)} </style></head>
<body><main>
<div class='hero'><h1>راهنمای My-AI</h1><p>راهنمای استفاده، یادگیری پیوسته، امنیت، کاربران و API</p></div>
<p>این صفحه برای استفاده همزمان با برنامه طراحی شده است. هر بخش رابط کاربری دکمه «راهنما» دارد و همین صفحه را در یک تب جدید، روی بخش مربوط، باز می‌کند.</p>
<nav><a href="#assistant">دستیار راهنما</a><a href="/help/local?component=self-development" target="_blank">خودپایش و توسعه</a><a href="#access">کاربران و دسترسی</a><a href="#local-files">راهنماهای محلی</a>
<a href="#chat">دستورها</a><a href="#learning">یادگیری</a><a href="#coding">برنامه‌نویسی</a><a href="#security">امنیت و پن‌تست</a><a href="#git">Git/GitHub</a><a href="#github-online">راهنمای آنلاین GitHub</a><a href="#memory">حافظه</a><a href="#scheduler">یادگیری خودکار</a><a href="#voice">صدا</a><a href="#api">API</a><a href="#docker">Docker</a><a href="#projects">پروژه</a><a href="#weblearn">URL Learning</a><a href="#practice">تمرین</a><a href="#coderun">Code Run</a>
</nav>
<section id="local-files" class="card"><h2>راهنماهای محلی مستقل</h2><p>هر بخش فایل راهنمای مستقل دارد و بدون اینترنت قابل خواندن است. سؤال را از My-AI بپرسید؛ اگر اطلاعات محلی کافی نباشد، مستندات آنلاین بررسی می‌شود و فقط بعد از تأیید شما فایل محلی تغییر می‌کند.</p><div><a href="/help/local?component=chat" target="_blank">چت و گفتگو</a> · <a href="/help/local?component=learning" target="_blank">یادگیری</a> · <a href="/help/local?component=coding" target="_blank">برنامه‌نویسی</a> · <a href="/help/local?component=security" target="_blank">امنیت و پن‌تست</a> · <a href="/help/local?component=git" target="_blank">Git / GitHub</a> · <a href="/help/local?component=memory" target="_blank">حافظه</a> · <a href="/help/local?component=scheduler" target="_blank">Scheduler</a> · <a href="/help/local?component=voice" target="_blank">صدا</a> · <a href="/help/local?component=api" target="_blank">API</a> · <a href="/help/local?component=docker" target="_blank">Docker</a> · </div></section><section id="assistant" class="card"><h2>پرسش از خود My-AI درباره راهنما</h2><p>اگر نمی‌دانید یک قابلیت را چطور استفاده کنید، سؤال را همین‌جا بپرسید. دستیار هم راهنمای داخلی را بررسی می‌کند و هم در وب مستندات جدید را جست‌وجو می‌کند.</p><textarea id="helpq" rows="3" style="width:100%;box-sizing:border-box;padding:10px" placeholder="مثلاً: GitHub را چطور به My-AI وصل کنم؟ اگر روش GitHub عوض شده بررسی کن"></textarea><button onclick="askHelp()">پرسش</button><pre id="helpanswer"></pre><div id="proposal"></div><script>
async function askHelp(){const q=document.getElementById("helpq").value.trim();if(!q)return;const a=document.getElementById("helpanswer");a.textContent="در حال بررسی راهنمای داخلی و مستندات وب...";const r=await fetch("/help/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q})});const j=await r.json();a.textContent=j.answer+"\n\nSources:\n"+(j.sources||[]).join("\n");const p=document.getElementById("proposal");if(j.proposed_update&&j.proposed_update!=="NO_CHANGE"){p.textContent="";const box=document.createElement("div");box.className="tip";const b=document.createElement("b");b.textContent="پیشنهاد تغییر راهنما:";const pre=document.createElement("pre");pre.textContent=j.proposed_update;const ok=document.createElement("button");ok.textContent="تأیید و اعمال در راهنما";ok.onclick=()=>approve(j.id);const no=document.createElement("button");no.textContent="رد";no.onclick=()=>reject(j.id);box.append(b,pre,ok,no);p.appendChild(box)}else p.textContent="تغییری برای راهنما پیشنهاد نشده است."}
async function approve(id){const r=await fetch("/help/approve/"+id,{method:"POST"});document.getElementById("proposal").textContent=(await r.json()).message}
async function reject(id){const r=await fetch("/help/reject/"+id,{method:"POST"});document.getElementById("proposal").textContent=(await r.json()).message}
</script></section><section id="chat" class="card"><h2>دستورها و چت</h2><p>صفحه اصلی محل اجرای دستورهای طبیعی است.</p><div class="cmd">پایتون یاد بگیر<br>PHP یاد بگیر<br>یک برنامه مدیریت فایل با پایتون بنویس<br>از پروژه مسیر: /path/to/project پن‌تست بگیر<br>از پروژه آدرس: https://example.com پن‌تست بگیر و فقط گزارش بده</div><div class="tip">برای هدف خارجی، آدرس باید صریحاً توسط شما داده شود. «فقط گزارش بده» یا «فقط تست بگیر» حالت بدون اصلاح است.</div></section>
<section id="learning" class="card"><h2>یادگیری پیوسته</h2><p>هر موضوع از curriculum پایه شروع می‌شود و سپس منابع رسمی، استانداردها، مستندات اکوسیستم، release notes، testing، security، performance و production را نیز بررسی می‌کند.</p><div class="cmd">پایتون یاد بگیر<br>PHP یاد بگیر<br>پن‌تست یاد بگیر</div><p>پس از تکمیل کامل یک domain، هر ۷ روز یک review اجرا می‌شود. مطالب جدید به curriculum قبلی اضافه می‌شوند و اگر مطلب جدید پیدا شود، آموزش آن به‌صورت خودکار شروع و در داشبورد نمایش داده می‌شود.</p><p>توقف دستی یک مسیر، شروع خودکار آن مسیر را متوقف می‌کند؛ با «ادامه» دوباره فعال می‌شود.</p></section>
<section id="coding" class="card"><h2>تولید و اجرای کد</h2><div class="cmd">یک API با پایتون بساز<br>یک پروژه PHP برای مدیریت کاربران بساز<br>یک برنامه JavaScript بنویس</div><p>اعتبارسنجی و اجرای خودکار فعلی برای Python محدود و کنترل‌شده است؛ زبان‌های دیگر عمدتاً تولید می‌شوند.</p></section>
<section id="security" class="card"><h2>بررسی امنیتی و پن‌تست</h2><p>پروژه محلی با تحلیل static بررسی می‌شود؛ DAST پویا فقط با sandbox تأییدشده فعال است. URL خارجیِ صریح با بررسی HTTP غیرمخرب بررسی می‌شود.</p><div class="cmd">از پروژه مسیر: /path/to/project پن‌تست بگیر<br>از پروژه مسیر: /path/to/project فقط گزارش بده<br>از پروژه آدرس: https://target.example پن‌تست بگیر<br>از پروژه آدرس: https://target.example فقط گزارش بده</div><p>مواردی مانند هدرهای امنیتی، خطای 500، debug leakage، reflection، TRACE، کوکی و نشانه‌های CSRF بررسی می‌شوند. اسکن خارجی از راه دور اصلاح نمی‌کند.</p><div class="warn">فقط سامانه‌ای را بررسی کنید که مالک آن هستید یا مجوز صریح تست آن را دارید.</div></section>
<section id="git" class="card"><h2>اتصال Git / GitHub</h2><p>خواندن repository، tree، فایل‌ها، issueها، pull requestها و branchها پشتیبانی می‌شود. نوشتن فقط با فعال‌سازی صریح مجاز است.</p><h3>توکن از کجا؟</h3><p>در GitHub مسیر <b>Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token</b> را باز کنید. برای <b>cognitive-kernel/My-ai</b>، در Repository access همان مخزن را انتخاب کنید. برای خواندن کد، <b>Contents: Read</b> کافی است؛ برای تغییر فایل/branch باید مجوز نوشتن متناظر را اضافه کنید.</p><p><a href="https://github.com/settings/personal-access-tokens/new" target="_blank">ساخت توکن</a> · توکن‌های GitHub معمولاً با <code>github_pat_</code> (fine-grained) یا <code>ghp_</code> (classic) شروع می‌شوند. توکن را مثل رمز عبور نگه دارید.</p><h3>حالت آفلاین</h3><p>همین بخش راهنمای داخلی برنامه است و بدون اینترنت قابل نمایش است. توکن ذخیره‌شده در فایل محلی <code>data/.github_token</code> نگه‌داری می‌شود و وارد Git نمی‌شود.</p><h3>توکن</h3><p><code>GITHUB_TOKEN</code> را تنظیم کنید. برای GitHub Enterprise، <code>GITHUB_API_URL</code> را هم تنظیم کنید.</p><div class="cmd">export GITHUB_TOKEN="YOUR_TOKEN"</div><h3>تست اتصال</h3><div class="cmd">GET /git/repo?repository=owner/repo<br>GET /git/tree?repository=owner/repo&ref=main<br>GET /git/file?repository=owner/repo&path=README.md<br>GET /git/issues?repository=owner/repo<br>GET /git/pulls?repository=owner/repo<br>GET /git/branches?repository=owner/repo</div><h3>نوشتن</h3><p>برای branch و update فایل، <code>allow_write=true</code> لازم است.</p><div class="cmd">POST /git/branch<br>{"repository":"owner/repo","branch":"my-ai-fix","ref":"main","allow_write":true}</div><div class="cmd">PUT /git/file<br>{"repository":"owner/repo","path":"app.py","content":"...","message":"My-AI: security fix","branch":"my-ai-fix","allow_write":true}</div><div class="tip">عیب‌یابی: token ← owner/repo ← مجوز token ← API URL در Enterprise.</div></section>
<section id="github-online" class="card"><h2>بررسی آنلاین راهنمای GitHub</h2><p>در این بخش My-AI سؤال شما را با راهنمای داخلی و مستندات آنلاین GitHub مقایسه می‌کند. اگر تغییر واقعی در مستندات لازم باشد، پیشنهاد تغییر ایجاد می‌شود و فقط بعد از زدن «تأیید و اعمال در راهنما» ثبت می‌شود.</p><p>پس از تأیید، نسخه تأییدشده در همین راهنمای محلی نمایش داده می‌شود؛ بنابراین راهنمای آفلاین نیز به‌روزرسانی می‌شود.</p><div class="cmd">مثال: «روش ساخت fine-grained token برای cognitive-kernel/My-ai را با مستندات فعلی GitHub بررسی کن.»</div></section><section id="access" class="card"><h2>کاربران و دسترسی‌ها</h2><p>کاربران دارای نقش و permissionهای جداگانه هستند. سطح‌های عملیاتی شامل <code>read</code>، <code>write</code> و <code>execute</code> است.</p><p>ابزارهای حساس مانند اجرای کد، GitHub write، امنیت، database، self-update و self-repair باید permission مناسب داشته باشند. تنظیمات حساس فقط برای administrator در دسترس است و رویدادهای مهم audit می‌شوند.</p><p>مدیریت کاربران و permissionهای per-tool از بخش Settings انجام می‌شود.</p></section><section id="memory" class="card"><h2>حافظه و دانش</h2><p>دانش، گفتگوها، جلسات یادگیری، آزمایش‌ها و taskهای پروژه در SQLite ذخیره می‌شوند.</p><div class="cmd">GET /memory/knowledge<br>GET /memory/search?q=python&limit=8<br>GET /projects/tasks</div></section>
<section id="scheduler" class="card"><h2>یادگیری خودکار</h2><p>Scheduler در پس‌زمینه مرحله‌های curriculum را اجرا می‌کند و review هفتگی را مدیریت می‌کند.</p><div class="cmd">POST /learning/learn<br>{"language":"Python","interval_seconds":3600}<br><br>GET /scheduler/status<br>POST /scheduler/stop</div><p>بازه مجاز فعلی ۶۰ ثانیه تا ۲۴ ساعت است.</p></section>
<section id="voice" class="card"><h2>گفتار و صدا</h2><p>ورودی گفتاری از Speech Recognition و خروجی از Speech Synthesis مرورگر استفاده می‌کند. زبان را از انتخابگر مشخص کنید.</p><div class="warn">پشتیبانی Speech Recognition به مرورگر وابسته است.</div></section>
<section id="api" class="card"><h2>API</h2><p><a href="/docs" target="_blank">Swagger UI — /docs</a> · <a href="/redoc" target="_blank">ReDoc — /redoc</a></p><p>Endpointهای اصلی شامل chat، learning، code، security، Git، memory، projects و scheduler هستند.</p></section><section id="projects" class="card"><h2>پروژه و برنامه‌ریزی</h2><p>برای تبدیل هدف به task از planner استفاده کنید و taskهای ذخیره‌شده را از حافظه پروژه ببینید.</p><div class="cmd">POST /projects/plan<br>{"goal":"ساخت یک API مدیریت کاربران"}<br><br>GET /projects/tasks</div></section><section id="weblearn" class="card"><h2>یادگیری از URL</h2><p>برای وارد کردن یک منبع مشخص به یادگیری، URL و موضوع را بدهید.</p><div class="cmd">POST /learn/url<br>{"url":"https://docs.python.org/3/","topic":"Python"}</div></section><section id="practice" class="card"><h2>تمرین و ارزیابی</h2><p>تمرین را به engine بدهید تا پاسخ را بررسی کند و نتیجه در روند یادگیری ثبت شود.</p><div class="cmd">POST /learning/practice<br>{"message":"تفاوت list و tuple در Python چیست؟"}</div></section><section id="image" class="card"><h2>ساخت تصویر</h2><p>صفحه «ساخت تصویر» تنها محل ثبت درخواست تولید تصویر است. در چت اصلی درخواست تصویر اجرا نمی‌شود و به این صفحه هدایت می‌شود.</p><div class="cmd">درخواست را در صفحه ساخت تصویر وارد کنید و «ساخت تصویر» را بزنید.</div></section>
<section id="settings" class="card"><h2>تنظیمات و صفحات تنظیمات</h2><p>صفحه تنظیمات به بخش‌های مستقل تقسیم شده است: GitHub، Self-Update، Self-Repair، یادگیری، منابع سیستم، کاربران، مجوزها، آموزش‌های سفارشی، لاگ‌ها و تنظیمات ساخت تصویر. از صفحه فهرست تنظیمات وارد هر بخش شوید.</p></section>
<section id="health" class="card"><h2>گزارش سلامت</h2><p>صفحه گزارش سلامت حذف نشده است و گزارش‌های خودپایش، تست‌ها، وضعیت سالم/نیازمند بررسی و تاریخچه گزارش‌ها را نمایش می‌دهد.</p></section>
<section id="chat-help" class="card"><h2>راهنمای چت اصلی</h2><p>چت اصلی برای گفتگوی عادی، پرسش، تولید کد و استفاده از دانش یادگرفته‌شده است. دستورهای یادگیری و تولید تصویر در این صفحه اجرا نمی‌شوند.</p></section>
<section id="coderun" class="card"><h2>اجرای/اعتبارسنجی کد</h2><p>اعتبارسنجی کد از endpoint مربوط به code استفاده می‌کند و اجرای Python محدود به کنترل‌های پروژه است.</p><div class="cmd">POST /code/run<br>{"code":"print(2+2)"}</div></section><section id="securityhistory" class="card"><h2>تاریخچه امنیت</h2><p>نتایج اسکن‌های امنیتی ذخیره می‌شوند و قابل مشاهده‌اند.</p><div class="cmd">GET /security/history?limit=20</div></section>
<section id="docker" class="card"><h2>Docker</h2><div class="cmd">docker compose up --build</div><p>پس از بالا آمدن سرویس، صفحه اصلی و این راهنما از همان سرویس قابل دسترسی هستند.</p></section>
<section class="card"><h2>عیب‌یابی سریع</h2><ul><li><b>مدل پاسخ نمی‌دهد:</b> Ollama و نام مدل را بررسی کنید.</li><li><b>یادگیری وب کار نمی‌کند:</b> URL منبع و دسترسی شبکه را بررسی کنید.</li><li><b>Git وصل نمی‌شود:</b> GITHUB_TOKEN، repository و مجوز token را بررسی کنید.</li><li><b>پن‌تست اجرا نمی‌شود:</b> مسیر پروژه، runtime و وابستگی‌ها را بررسی کنید.</li><li><b>URL خارجی رد می‌شود:</b> باید http/https باشد و به IP عمومی resolve شود.</li><li><b>اصلاح نمی‌خواهید:</b> «فقط گزارش بده» یا «فقط تست بگیر» را بگویید.</li></ul></section>
</main></body></html>"""

def page():
    updates = fetch_all("SELECT * FROM help_updates WHERE status='approved' ORDER BY id DESC LIMIT 30")
    extra = "".join(
        f"<section class='card'><h2>به‌روزرسانی راهنما: {u['component']}</h2>"
        f"<p>{escape(u['proposed_update'] or u['answer'])}</p><p><small>منابع: {escape(u['sources'] or '')}</small></p></section>"
        for u in updates
    )
    return HTML.replace("</main></body></html>", extra + "</main></body></html>")

def ask_help(question, component, llm, web):
    domains = {
        "git": ["docs.github.com", "github.com"],
        "security": ["owasp.org", "portswigger.net", "nmap.org"],
        "python": ["docs.python.org"],
        "php": ["php.net", "getcomposer.org"],
        "javascript": ["developer.mozilla.org"],
        "docker": ["docs.docker.com"],
        "api": ["fastapi.tiangolo.com"],
    }.get(component.lower(), None)
    results = web.search(question, domains=domains, limit=6)
    fetched = []
    for item in results[:4]:
        try:
            title, body = web.fetch(item["url"])
            fetched.append({"title": title, "url": item["url"], "content": body[:12000]})
        except Exception:
            fetched.append(item)
    answer = llm.chat(
        "Answer the user's question about using this My-AI feature. Be practical and concise. "
        "If current external integration instructions may have changed, distinguish the current documented method from the project's existing implementation. "
        "Do not invent steps. Sources are supplied below. QUESTION: "+question+
        "\nCOMPONENT: "+component+"\nSOURCES:\n"+json.dumps(fetched,ensure_ascii=False),
        system="You are the My-AI product help assistant. Cite source URLs in plain text."
    )
    proposal = llm.chat(
        "Compare the current project help instructions with the supplied current documentation. "
        "Return a concise proposed help update only if a real change is needed; otherwise return NO_CHANGE. "
        "Never modify anything yourself.\nQUESTION:"+question+
        "\nCURRENT LOCAL HELP:\n"+local_help(component)+"\nLEGACY HELP:\n"+HTML+
        "\nCURRENT SOURCES:\n"+json.dumps(fetched,ensure_ascii=False),
        system="Return either NO_CHANGE or a short proposed replacement/addition for the relevant help section."
    )
    rid=execute("INSERT INTO help_updates(component,question,status,answer,sources,proposed_update) VALUES(?,?,?,?,?,?)",
                (component,question,"pending",answer,json.dumps([x.get("url") for x in fetched],ensure_ascii=False),proposal))
    return {"id":rid,"component":component,"answer":answer,"sources":[x.get("url") for x in fetched],"proposed_update":proposal,"status":"pending"}
