from __future__ import annotations
import json
from .db import execute, fetch_all

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
</style></head>
<body><main>
<h1>راهنمای My-AI</h1>
<p>این صفحه برای استفاده همزمان با برنامه طراحی شده است. هر بخش رابط کاربری دکمه «راهنما» دارد و همین صفحه را در یک تب جدید، روی بخش مربوط، باز می‌کند.</p>
<nav>
<a href="#chat">دستورها</a><a href="#learning">یادگیری</a><a href="#coding">برنامه‌نویسی</a><a href="#security">امنیت و پن‌تست</a><a href="#git">Git/GitHub</a><a href="#memory">حافظه</a><a href="#scheduler">یادگیری خودکار</a><a href="#voice">صدا</a><a href="#api">API</a><a href="#docker">Docker</a><a href="#projects">پروژه</a><a href="#weblearn">URL Learning</a><a href="#practice">تمرین</a><a href="#coderun">Code Run</a>
</nav>
<section id="chat" class="card"><h2>دستورها و چت</h2><p>صفحه اصلی محل اجرای دستورهای طبیعی است.</p><div class="cmd">پایتون یاد بگیر<br>PHP یاد بگیر<br>یک برنامه مدیریت فایل با پایتون بنویس<br>از پروژه مسیر: /path/to/project پن‌تست بگیر<br>از پروژه آدرس: https://example.com پن‌تست بگیر و فقط گزارش بده</div><div class="tip">برای هدف خارجی، آدرس باید صریحاً توسط شما داده شود. «فقط گزارش بده» یا «فقط تست بگیر» حالت بدون اصلاح است.</div></section>
<section id="learning" class="card"><h2>یادگیری و حافظه دانشی</h2><p>یادگیری curriculum را دنبال می‌کند، منابع را می‌خواند و دانش و پیشرفت را در SQLite نگه می‌دارد.</p><div class="cmd">پایتون یاد بگیر<br>PHP یاد بگیر<br>پن‌تست یاد بگیر</div><p>برای یک مرحله از دکمه‌های یادگیری سریع و برای اجرای پیوسته از Scheduler استفاده کنید.</p></section>
<section id="coding" class="card"><h2>تولید و اجرای کد</h2><div class="cmd">یک API با پایتون بساز<br>یک پروژه PHP برای مدیریت کاربران بساز<br>یک برنامه JavaScript بنویس</div><p>اعتبارسنجی و اجرای خودکار فعلی برای Python محدود و کنترل‌شده است؛ زبان‌های دیگر عمدتاً تولید می‌شوند.</p></section>
<section id="security" class="card"><h2>بررسی امنیتی و پن‌تست</h2><p>پروژه محلی با static + DAST بررسی می‌شود و URL خارجیِ صریح با بررسی HTTP غیرمخرب.</p><div class="cmd">از پروژه مسیر: /path/to/project پن‌تست بگیر<br>از پروژه مسیر: /path/to/project فقط گزارش بده<br>از پروژه آدرس: https://target.example پن‌تست بگیر<br>از پروژه آدرس: https://target.example فقط گزارش بده</div><p>مواردی مانند هدرهای امنیتی، خطای 500، debug leakage، reflection، TRACE، کوکی و نشانه‌های CSRF بررسی می‌شوند. اسکن خارجی از راه دور اصلاح نمی‌کند.</p><div class="warn">فقط سامانه‌ای را بررسی کنید که مالک آن هستید یا مجوز صریح تست آن را دارید.</div></section>
<section id="git" class="card"><h2>اتصال Git / GitHub</h2><p>خواندن repository، tree، فایل‌ها، issueها، pull requestها و branchها پشتیبانی می‌شود. نوشتن فقط با فعال‌سازی صریح مجاز است.</p><h3>توکن</h3><p><code>GITHUB_TOKEN</code> را تنظیم کنید. برای GitHub Enterprise، <code>GITHUB_API_URL</code> را هم تنظیم کنید.</p><div class="cmd">export GITHUB_TOKEN="YOUR_TOKEN"</div><h3>تست اتصال</h3><div class="cmd">GET /git/repo?repository=owner/repo<br>GET /git/tree?repository=owner/repo&ref=main<br>GET /git/file?repository=owner/repo&path=README.md<br>GET /git/issues?repository=owner/repo<br>GET /git/pulls?repository=owner/repo<br>GET /git/branches?repository=owner/repo</div><h3>نوشتن</h3><p>برای branch و update فایل، <code>allow_write=true</code> لازم است.</p><div class="cmd">POST /git/branch<br>{"repository":"owner/repo","branch":"my-ai-fix","ref":"main","allow_write":true}</div><div class="cmd">PUT /git/file<br>{"repository":"owner/repo","path":"app.py","content":"...","message":"My-AI: security fix","branch":"my-ai-fix","allow_write":true}</div><div class="tip">عیب‌یابی: token ← owner/repo ← مجوز token ← API URL در Enterprise.</div></section>
<section id="memory" class="card"><h2>حافظه و دانش</h2><p>دانش، گفتگوها، جلسات یادگیری، آزمایش‌ها و taskهای پروژه در SQLite ذخیره می‌شوند.</p><div class="cmd">GET /memory/knowledge<br>GET /memory/search?q=python&limit=8<br>GET /projects/tasks</div></section>
<section id="scheduler" class="card"><h2>یادگیری خودکار</h2><p>Scheduler در پس‌زمینه مرحله‌های curriculum را اجرا می‌کند.</p><div class="cmd">POST /learning/learn<br>{"language":"Python","interval_seconds":3600}<br><br>GET /scheduler/status<br>POST /scheduler/stop</div><p>بازه مجاز فعلی ۶۰ ثانیه تا ۲۴ ساعت است.</p></section>
<section id="voice" class="card"><h2>گفتار و صدا</h2><p>ورودی گفتاری از Speech Recognition و خروجی از Speech Synthesis مرورگر استفاده می‌کند. زبان را از انتخابگر مشخص کنید.</p><div class="warn">پشتیبانی Speech Recognition به مرورگر وابسته است.</div></section>
<section id="api" class="card"><h2>API</h2><p><a href="/docs" target="_blank">Swagger UI — /docs</a> · <a href="/redoc" target="_blank">ReDoc — /redoc</a></p><p>Endpointهای اصلی شامل chat، learning، code، security، Git، memory، projects و scheduler هستند.</p></section><section id="projects" class="card"><h2>پروژه و برنامه‌ریزی</h2><p>برای تبدیل هدف به task از planner استفاده کنید و taskهای ذخیره‌شده را از حافظه پروژه ببینید.</p><div class="cmd">POST /projects/plan<br>{"goal":"ساخت یک API مدیریت کاربران"}<br><br>GET /projects/tasks</div></section><section id="weblearn" class="card"><h2>یادگیری از URL</h2><p>برای وارد کردن یک منبع مشخص به یادگیری، URL و موضوع را بدهید.</p><div class="cmd">POST /learn/url<br>{"url":"https://docs.python.org/3/","topic":"Python"}</div></section><section id="practice" class="card"><h2>تمرین و ارزیابی</h2><p>تمرین را به engine بدهید تا پاسخ را بررسی کند و نتیجه در روند یادگیری ثبت شود.</p><div class="cmd">POST /learning/practice<br>{"message":"تفاوت list و tuple در Python چیست؟"}</div></section><section id="coderun" class="card"><h2>اجرای/اعتبارسنجی کد</h2><p>اعتبارسنجی کد از endpoint مربوط به code استفاده می‌کند و اجرای Python محدود به کنترل‌های پروژه است.</p><div class="cmd">POST /code/run<br>{"code":"print(2+2)"}</div></section><section id="securityhistory" class="card"><h2>تاریخچه امنیت</h2><p>نتایج اسکن‌های امنیتی ذخیره می‌شوند و قابل مشاهده‌اند.</p><div class="cmd">GET /security/history?limit=20</div></section>
<section id="docker" class="card"><h2>Docker</h2><div class="cmd">docker compose up --build</div><p>پس از بالا آمدن سرویس، صفحه اصلی و این راهنما از همان سرویس قابل دسترسی هستند.</p></section>
<section class="card"><h2>عیب‌یابی سریع</h2><ul><li><b>مدل پاسخ نمی‌دهد:</b> Ollama و نام مدل را بررسی کنید.</li><li><b>یادگیری وب کار نمی‌کند:</b> URL منبع و دسترسی شبکه را بررسی کنید.</li><li><b>Git وصل نمی‌شود:</b> GITHUB_TOKEN، repository و مجوز token را بررسی کنید.</li><li><b>پن‌تست اجرا نمی‌شود:</b> مسیر پروژه، runtime و وابستگی‌ها را بررسی کنید.</li><li><b>URL خارجی رد می‌شود:</b> باید http/https باشد و به IP عمومی resolve شود.</li><li><b>اصلاح نمی‌خواهید:</b> «فقط گزارش بده» یا «فقط تست بگیر» را بگویید.</li></ul></section>
</main></body></html>"""

def page():
    updates = fetch_all("SELECT * FROM help_updates WHERE status='approved' ORDER BY id DESC LIMIT 30")
    extra = "".join(
        f"<section class='card'><h2>به‌روزرسانی راهنما: {u['component']}</h2>"
        f"<p>{u['answer']}</p><p><small>منابع: {u['sources']}</small></p></section>"
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
        "\nCURRENT HELP:\n"+HTML+
        "\nCURRENT SOURCES:\n"+json.dumps(fetched,ensure_ascii=False),
        system="Return either NO_CHANGE or a short proposed replacement/addition for the relevant help section."
    )
    rid=execute("INSERT INTO help_updates(component,question,status,answer,sources,proposed_update) VALUES(?,?,?,?,?,?)",
                (component,question,"pending",answer,json.dumps([x.get("url") for x in fetched],ensure_ascii=False),proposal))
    return {"id":rid,"component":component,"answer":answer,"sources":[x.get("url") for x in fetched],"proposed_update":proposal,"status":"pending"}
