from __future__ import annotations

import json
import logging
import re
from html import escape
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)

NAV_STYLE = """
<style id="myAiGlobalNavStyle">
.myai-nav{position:sticky;top:0;z-index:9999;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 14px;margin:0 0 14px;border:1px solid #dbe3ef;border-radius:16px;background:rgba(255,255,255,.94);backdrop-filter:blur(14px);box-shadow:0 8px 28px #0f172a12;font-family:Tahoma,system-ui,sans-serif;direction:rtl}
.myai-nav .brand{font-weight:900;color:#0f172a;text-decoration:none;padding:8px 10px;margin-left:auto}.myai-nav a{color:#334155;text-decoration:none;padding:8px 10px;border-radius:10px;font-size:13px}.myai-nav a:hover,.myai-nav a.active{background:#eef2ff;color:#1d4ed8}.myai-nav .group{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.myai-nav .sep{width:1px;height:24px;background:#e2e8f0}.myai-nav .help{background:#1d4ed8;color:#fff;font-weight:800}.myai-page{max-width:1180px;margin:auto;padding:20px;font-family:Tahoma,system-ui,sans-serif;direction:rtl}.myai-card{background:#fff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 28px #0f172a0b;padding:18px;margin:12px 0}.myai-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}.myai-link{display:flex;flex-direction:column;gap:7px;padding:18px;background:#fff;border:1px solid #e5e7eb;border-radius:16px;text-decoration:none;color:#17202a;box-shadow:0 8px 24px #0f172a0b}.myai-link:hover{border-color:#93c5fd;transform:translateY(-1px)}.myai-muted{color:#64748b;font-size:13px;line-height:1.9}.myai-page textarea,.myai-page input,.myai-page select{box-sizing:border-box;width:100%;padding:11px;border:1px solid #cbd5e1;border-radius:12px;font:inherit}.myai-page textarea{min-height:130px;resize:vertical}.myai-page button{padding:10px 14px;border:0;border-radius:10px;background:#1d4ed8;color:#fff;font-weight:800;cursor:pointer}.myai-page button.secondary{background:#eef2ff;color:#1e3a8a}.myai-status{padding:10px;border-radius:10px;background:#f8fafc;white-space:pre-wrap}.myai-progress{height:24px;background:#e2e8f0;border-radius:9px;overflow:hidden}.myai-progress>span{display:block;height:100%;background:#2563eb;color:#fff;text-align:center;line-height:24px;font-size:12px}.myai-result img{max-width:100%;border-radius:16px;border:1px solid #e2e8f0}.myai-helpbox{background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:12px;line-height:1.9}@media(max-width:800px){.myai-page{padding:12px}.myai-nav .brand{width:100%;margin-left:0}}
</style>
"""


def _nav(path: str, help_anchor: str | None = None) -> str:
    if help_anchor is None:
        help_anchor = 'chat' if path == '/' else ('learning' if path.startswith('/learning') else ('image' if path.startswith('/image') else ('health' if path.startswith('/self-diagnostics') else ('settings' if path.startswith('/settings') else 'page-help'))))
    def active(prefix: str) -> str:
        return " active" if path == prefix or path.startswith(prefix + "/") else ""
    return f"""
<nav class="myai-nav" id="myAiGlobalNav">
<a class="brand" href="/">My-AI</a>
<div class="group"><a class="{active('/')}" href="/">چت اصلی</a><a class="{active('/learning')}" href="/learning">پیشرفت و یادگیری</a><a class="{active('/image')}" href="/image">ساخت تصویر</a></div>
<span class="sep"></span>
<div class="group"><a class="{active('/settings')}" href="/settings/sections">تنظیمات</a><a class="{active('/self-diagnostics')}" href="/self-diagnostics">گزارش سلامت</a><a class="{active('/help')}" href="/help">راهنمای کامل</a></div>
<a class="help" href="/help#{help_anchor}" target="_blank">راهنمای این صفحه</a>
</nav>"""

SETTINGS = [
("github","اتصال GitHub","احراز هویت، مخزن و اتصال GitHub"),
("update","Self-Update","بررسی و مدیریت به‌روزرسانی"),
("repair","Self-Repair","تنظیمات تعمیر و تأیید عملیات"),
("learning","یادگیری سریع","سرعت، فاصله و تلاش‌های یادگیری"),
("resource","منابع سیستم","CPU، RAM، Thread و GPU"),
("user","کاربران","مدیریت کاربران"),
("permission","مجوزها","مجوزهای ابزار برای کاربران"),
("course","آموزش‌های سفارشی","دوره‌ها و سرفصل‌های سفارشی"),
("log","لاگ‌ها","سطح و تنظیمات ثبت رویدادها"),
("image","ساخت تصویر","موتور و تنظیمات تولید تصویر"),
]


def _settings_sections() -> str:
    cards = ''.join(f'<a class="myai-link" href="/settings/section/{s}"><b>{escape(t)}</b><span class="myai-muted">{escape(d)}</span></a>' for s,t,d in SETTINGS)
    return f"<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>بخش‌های تنظیمات | My-AI</title>{NAV_STYLE}</head><body><main class='myai-page'>{_nav('/settings/sections')}<section class='myai-card'><h1>تنظیمات</h1><p class='myai-muted'>هر بخش تنظیمات صفحه مستقل دارد. امکانات قبلی حذف نشده‌اند.</p><div class='myai-grid'>{cards}</div></section></main></body></html>"


def _settings_section(slug: str) -> str:
    title = next((t for s,t,_ in SETTINGS if s == slug), "تنظیمات")
    return f"<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{escape(title)} | My-AI</title>{NAV_STYLE}</head><body><main class='myai-page'>{_nav('/settings/section/'+slug, slug+'-help')}<section class='myai-card'><h1>{escape(title)}</h1><p class='myai-muted'>تنظیمات این بخش در یک صفحه مستقل قرار دارد و از تنظیمات اصلی پروژه استفاده می‌کند.</p><iframe id='settingsFrame' src='/settings?section={escape(slug)}' style='width:100%;height:calc(100vh - 230px);min-height:650px;border:1px solid #e5e7eb;border-radius:14px;background:#fff' title='{escape(title)}'></iframe><div class='myai-helpbox'>راهنمای این صفحه: برای توضیح کامل قابلیت‌های این بخش، <a href='/help#settings-help' target='_blank'>راهنمای تنظیمات</a> را باز کنید.</div><script>(function(){{var f=document.getElementById('settingsFrame');f.addEventListener('load',function(){{try{{var d=f.contentDocument||f.contentWindow.document;var wanted={json.dumps(title,ensure_ascii=False)};var aliases={{github:['GitHub','گیت'],update:['Self-Update','به‌روزرسانی'],repair:['Self-Repair','تعمیر'],learning:['یادگیری'],resource:['منابع','CPU','RAM'],user:['کاربران'],permission:['مجوز'],course:['آموزش‌های سفارشی','دوره'],log:['لاگ'],image:['ساخت تصویر','Image']}};var keys=aliases[{json.dumps(slug)}]||[wanted];var els=[...d.querySelectorAll('.card,section,fieldset,details')];var hits=els.filter(function(e){{var t=(e.innerText||'').toLowerCase();return keys.some(function(k){{return t.indexOf(String(k).toLowerCase())>=0}})}});if(hits.length){{els.forEach(function(e){{if(!hits.includes(e)&&e!==d.body&&e.querySelector('h1,h2,h3,h4'))e.style.display='none'}});hits[0].scrollIntoView({{block:'start'}})}}}}catch(e){{}}}})}})();</script></section></main></body></html>"


def _image_page() -> str:
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ساخت تصویر | My-AI</title>{NAV_STYLE}</head><body><main class='myai-page'>{_nav('/image', 'image')}<section class='myai-card'><h1>ساخت تصویر</h1><p class='myai-muted'>این صفحه تنها محل ثبت درخواست ساخت تصویر است. چت اصلی اجازه اجرای درخواست تصویر را ندارد.</p><div class='myai-grid'><div><label>درخواست تصویر</label><textarea id='prompt' placeholder='مثلاً: یک داشبورد مدرن برای یک دستیار هوش مصنوعی محلی...'></textarea><div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px'><select id='size'><option value='1024x1024'>1024×1024</option><option value='1536x1024'>1536×1024</option><option value='1024x1536'>1024×1536</option></select><select id='quality'><option value='high'>کیفیت بالا</option><option value='standard'>استاندارد</option></select></div><button id='go' style='margin-top:10px'>ساخت تصویر</button><p id='status' class='myai-status'></p></div><div id='result' class='myai-result'></div></div></section></main><script>const $=id=>document.getElementById(id);$('go').onclick=async()=>{{const prompt=$('prompt').value.trim();if(!prompt){{$('status').textContent='درخواست تصویر را وارد کنید.';return}}$('go').disabled=true;$('status').textContent='در حال ساخت...';$('result').innerHTML='';try{{const r=await fetch('/image/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{prompt,size:$('size').value,quality:$('quality').value}})}});const j=await r.json();if(!r.ok)throw Error(j.detail||'خطا');if(j.url){{$('result').innerHTML='<img src="'+j.url+'" alt="generated"><p><a href="'+j.url+'" target="_blank">باز کردن تصویر</a></p>'}}else $('result').textContent=JSON.stringify(j,null,2);$('status').textContent='تصویر آماده شد.'}}catch(e){{$('status').textContent='خطا: '+e.message}}finally{{$('go').disabled=false}}}};</script></body></html>"""


def _learning_page() -> str:
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>پیشرفت و یادگیری | My-AI</title>{NAV_STYLE}</head><body><main class='myai-page'>{_nav('/learning', 'learning')}<section class='myai-card'><h1>پیشرفت و یادگیری</h1><p class='myai-muted'>این صفحه مخصوص دستورهای یادگیری است. «تجربه شخصی» باعث می‌شود درس‌های آموخته‌شده و خطاهای رخ‌داده به همان آموزش متصل و برای دفعات بعدی بازیابی شوند.</p><div class='myai-helpbox'><b>تجربه شخصی:</b> با فعال بودن این گزینه، My-AI درس‌های موفق، خطاهای منابع/ارزیابی و خطاهای عملیات حین یادگیری را ذخیره می‌کند و قبل از ادامه آموزش در اختیار موتور یادگیری قرار می‌دهد.</div><label style='display:flex;align-items:center;gap:10px;margin:12px 0'><input id='experienceToggle' type='checkbox' style='width:auto'> ذخیره و استفاده از تجربه شخصی برای این آموزش</label><textarea id='learnInput' placeholder='مثلاً: یاد بگیر Python'></textarea><div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px'><button id='learnBtn'>شروع یادگیری</button><button class='secondary' id='refreshBtn'>به‌روزرسانی پیشرفت</button><button class='secondary' id='experienceBtn'>نمایش تجربه‌های ذخیره‌شده</button></div><p id='learnStatus' class='myai-status'></p></section><section class='myai-card'><h2>پیشرفت فعلی</h2><div id='progress'>در حال بارگذاری...</div></section><section class='myai-card'><h2>تجربه شخصی این آموزش</h2><div id='experiences'>هنوز تجربه‌ای ثبت نشده است.</div></section></main><script>
const out=document.getElementById('learnStatus');
async function json(url,opt){{const r=await fetch(url,opt||{{cache:'no-store'}});const t=await r.text();let j={{}};try{{j=JSON.parse(t)}}catch{{j={{detail:t}}}}if(!r.ok)throw Error(j.detail||'HTTP '+r.status);return j}}
async function loadExperienceSetting(){{try{{const j=await json('/learning/experience/settings');document.getElementById('experienceToggle').checked=!!j.enabled}}catch(e){{out.textContent='خطا در خواندن تنظیم تجربه شخصی: '+e.message}}}}
document.getElementById('experienceToggle').onchange=async()=>{{try{{await json('/learning/experience/settings?enabled='+document.getElementById('experienceToggle').checked,{{method:'PATCH'}});out.textContent=document.getElementById('experienceToggle').checked?'تجربه شخصی فعال شد.':'تجربه شخصی غیرفعال شد.'}}catch(e){{out.textContent='خطا: '+e.message;await loadExperienceSetting()}}}};
async function refresh(){{try{{const j=await json('/learning/status');const p=Number(j.progress_percent||j.overall_percent||0);document.getElementById('progress').innerHTML='<div class="myai-progress"><span style="width:'+Math.max(0,Math.min(100,p))+'%">'+p+'%</span></div><pre>'+JSON.stringify(j,null,2)+'</pre>'}}catch(e){{document.getElementById('progress').textContent='خطا: '+e.message}}}}
async function experiences(){{try{{const j=await json('/learning/status');const rows=j.sessions||j.items||[];const topic=(rows[0]&&rows[0].topic)||'';const language=(rows[0]&&rows[0].language)||'';if(!topic||!language){{document.getElementById('experiences').textContent='هنوز آموزشی برای نمایش تجربه وجود ندارد.';return}}const x=await json('/learning/experiences?language='+encodeURIComponent(language)+'&topic='+encodeURIComponent(topic));document.getElementById('experiences').innerHTML=(x.items||[]).map(e=>'<article style="padding:10px;margin:8px 0;border:1px solid #e2e8f0;border-radius:10px"><b>'+String(e.kind||'').replace(/</g,'&lt;')+'</b> — '+String(e.action||'').replace(/</g,'&lt;')+'<div style="white-space:pre-wrap;margin-top:6px">'+String(e.content||'').replace(/</g,'&lt;')+'</div>'+(e.error?'<div style="color:#b91c1c;margin-top:5px">خطا: '+String(e.error).replace(/</g,'&lt;')+'</div>':'')+'</article>').join('')||'هنوز تجربه‌ای ثبت نشده است.'}}catch(e){{document.getElementById('experiences').textContent='خطا: '+e.message}}}}
document.getElementById('learnBtn').onclick=async()=>{{const message=document.getElementById('learnInput').value.trim();if(!message){{out.textContent='دستور یادگیری را وارد کنید.';return}}document.getElementById('learnBtn').disabled=true;out.textContent='در حال ثبت و اجرای یادگیری...';try{{const r=await json('/learning/command',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message,session_id:null,attachments:[]}})}});out.textContent=r.answer||JSON.stringify(r);await refresh();await experiences()}}catch(e){{out.textContent='خطا: '+e.message}}finally{{document.getElementById('learnBtn').disabled=false}}}};
document.getElementById('refreshBtn').onclick=refresh;document.getElementById('experienceBtn').onclick=experiences;loadExperienceSetting();refresh();experiences();
</script></body></html>"""

def _inject_global(body: str, path: str) -> str:
    if path == '/':
        body = body.replace("if(currentSessionId===null&&list.length)await selectChat(Number(list[0].id))", "")
        body = body.replace("loadLocalHistory();", "")
    nav = _nav(path)
    if 'id="myAiGlobalNav"' not in body:
        body = body.replace('<body>', '<body>'+NAV_STYLE+nav, 1)
    script = "<script>(function(){var n=document.getElementById('myAiGlobalNav');if(n&&n.parentElement!==document.body){document.body.insertBefore(n,document.body.firstChild)}})();</script>"
    return body.replace('</body>', script+'</body>', 1) if '</body>' in body else body+script


def install_ui_extensions(app) -> None:
    @app.get('/image', response_class=HTMLResponse)
    async def image_page():
        return HTMLResponse(_image_page(), headers={'Cache-Control':'no-store'})

    @app.get('/settings/sections', response_class=HTMLResponse)
    async def settings_sections_page():
        return HTMLResponse(_settings_sections(), headers={'Cache-Control':'no-store'})

    @app.get('/settings/section/{slug}', response_class=HTMLResponse)
    async def settings_section_page(slug: str):
        valid={s for s,_,_ in SETTINGS}
        if slug not in valid:return HTMLResponse(_settings_sections(),status_code=404)
        return HTMLResponse(_settings_section(slug), headers={'Cache-Control':'no-store'})

    @app.middleware('http')
    async def local_feature_ui(request, call_next):
        path=request.url.path
        if request.method=='POST' and path in {'/chat','/chat/stream'}:
            try:
                body=await request.body(); payload=json.loads(body.decode('utf-8') or '{}')
                msg=str(payload.get('message') or '')
                low=re.sub(r'\s+',' ',msg.casefold())
                referer=request.headers.get('referer','')
                learning_page=bool(re.search(r'/learning(?:[/?#]|$)',referer))
                learning=bool(re.search(r'(یاد\s*بگیر|یادگیری\s*را\s*شروع|آموزش\s*بده|learn\s+(?:about\s+)?|teach\s+yourself|start\s+learning)',low))
                image=bool(re.search(r'(ساخت\s*تصویر|ساختن\s*تصویر|تولید\s*تصویر|بساز.*تصویر|generate\s+(?:an?\s+)?image|create\s+(?:an?\s+)?image|make\s+(?:an?\s+)?image)',low))
                if image:return JSONResponse({'answer':'درخواست ساخت تصویر فقط در صفحه «ساخت تصویر» اجرا می‌شود.','redirect':'/image'},status_code=409)
                if learning and not learning_page:return JSONResponse({'answer':'این درخواست در صفحه چت اصلی اجرا نمی‌شود. برای یادگیری به «پیشرفت و یادگیری» بروید.','redirect':'/learning'},status_code=409)
            except json.JSONDecodeError as exc:
                logger.debug("UI_REQUEST_BODY_NOT_JSON: %s", exc)
        response=await call_next(request)
        if not hasattr(response,'body') or not response.body:return response
        content_type=response.headers.get('content-type','')
        if 'text/html' not in content_type or path in {'/login','/register'}:return response
        if path=='/learning':
            body=_learning_page()
        else:
            body=response.body.decode('utf-8',errors='replace')
            if path=='/help':
                guide="""<section id='page-help' style='margin:20px auto;max-width:1100px;padding:18px;background:#fff;border:1px solid #e5e7eb;border-radius:16px;font-family:Tahoma,system-ui,sans-serif;direction:rtl'><h2>راهنمای صفحات My-AI</h2><div class='myai-grid'><div><h3>چت اصلی</h3><p>گفتگوی عادی و تولید کد در این صفحه انجام می‌شود. یادگیری و ساخت تصویر عمداً از این صفحه جدا شده‌اند.</p></div><div id='learning-help'><h3>پیشرفت و یادگیری</h3><p>فقط دستورهای یادگیری را ثبت کنید؛ چت عمومی در این صفحه اجرا نمی‌شود. وضعیت و پیشرفت یادگیری نیز همین‌جا نمایش داده می‌شود.</p></div><div id='image-help'><h3>ساخت تصویر</h3><p>این صفحه فقط برای درخواست تولید تصویر است؛ ابزار تصویر در چت اصلی فعال نیست.</p></div><div id='settings-help'><h3>تنظیمات</h3><p>تنظیمات به صفحات مستقل GitHub، Self-Update، Self-Repair، یادگیری، منابع، کاربران، مجوزها، دوره‌های سفارشی، لاگ‌ها و ساخت تصویر تقسیم شده‌اند.</p></div><div id='github-help'><h3>اتصال GitHub</h3><p>تنظیمات API، repository، token و بررسی اتصال GitHub در این صفحه است.</p></div><div id='update-help'><h3>Self-Update</h3><p>فعال‌سازی، تأیید و Health URL مربوط به به‌روزرسانی خودکار را مدیریت می‌کند.</p></div><div id='repair-help'><h3>Self-Repair</h3><p>فعال‌سازی تعمیر خودکار و الزام تأیید عملیات تعمیر را مدیریت می‌کند.</p></div><div id='settings-learning-help'><h3>تنظیمات یادگیری</h3><p>سرعت یادگیری، فاصله اجرای worker و تنظیمات retry را کنترل می‌کند.</p></div><div id='resource-help'><h3>منابع سیستم</h3><p>سقف CPU، تعداد thread، RAM و GPU layers را کنترل می‌کند.</p></div><div id='user-help'><h3>کاربران</h3><p>ایجاد، فعال/غیرفعال‌سازی و نقش کاربران را مدیریت می‌کند.</p></div><div id='permission-help'><h3>مجوزها</h3><p>مجوزهای read/write/execute هر ابزار را برای کاربران مدیریت می‌کند.</p></div><div id='course-help'><h3>آموزش‌های سفارشی</h3><p>دوره، topic، هدف، منبع و وضعیت اجرای دوره‌های سفارشی را مدیریت می‌کند.</p></div><div id='log-help'><h3>لاگ‌ها</h3><p>سطح و تنظیمات ثبت رخدادهای سیستم را مدیریت می‌کند.</p></div><div id='settings-image-help'><h3>تنظیمات ساخت تصویر</h3><p>تنظیمات موتور و تولید تصویر را مدیریت می‌کند؛ خود درخواست تصویر در صفحه «ساخت تصویر» انجام می‌شود.</p></div><div><h3>گزارش سلامت</h3><p>وضعیت سلامت، تست‌ها و گزارش خطاهای سیستم از صفحه گزارش سلامت در دسترس است.</p></div></div></section>"""
                body=body.replace('</body>',guide+'</body>') if '</body>' in body else body+guide
            body=_inject_global(body,path)
        headers={k:v for k,v in response.headers.items() if k.lower() not in {'content-length','content-type'}}
        return HTMLResponse(body,status_code=response.status_code,headers=headers)
