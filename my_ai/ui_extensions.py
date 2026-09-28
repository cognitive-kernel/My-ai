from __future__ import annotations

import json
import re
from html import escape

from fastapi.responses import HTMLResponse, JSONResponse


NAV_STYLE = """
<style id="myAiGlobalNavStyle">
.myai-nav{position:sticky;top:0;z-index:9999;display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 14px;margin:0 0 14px;border:1px solid #dbe3ef;border-radius:16px;background:rgba(255,255,255,.92);backdrop-filter:blur(14px);box-shadow:0 8px 28px #0f172a12;font-family:Tahoma,system-ui,sans-serif;direction:rtl}
.myai-nav .brand{font-weight:900;color:#0f172a;text-decoration:none;padding:8px 10px;margin-left:auto}.myai-nav a{color:#334155;text-decoration:none;padding:8px 10px;border-radius:10px;font-size:13px}.myai-nav a:hover,.myai-nav a.active{background:#eef2ff;color:#1d4ed8}.myai-nav .group{display:flex;gap:4px;align-items:center;flex-wrap:wrap}.myai-nav .sep{width:1px;height:24px;background:#e2e8f0;margin:0 2px}.myai-page-help{display:inline-flex!important;background:#1d4ed8!important;color:#fff!important;font-weight:800!important}.myai-settings-shell{max-width:1180px;margin:20px auto;padding:0 14px;font-family:Tahoma,system-ui,sans-serif;direction:rtl}.myai-settings-shell .card{background:#fff;border:1px solid #e5e7eb;border-radius:18px;box-shadow:0 10px 28px #0f172a0b}.myai-settings-frame{width:100%;height:calc(100vh - 180px);min-height:680px;border:0;border-radius:18px;background:#fff}.myai-image-page{max-width:1100px;margin:20px auto;padding:0 14px;font-family:Tahoma,system-ui,sans-serif;direction:rtl}.myai-image-card{background:#fff;border:1px solid #e5e7eb;border-radius:20px;padding:20px;box-shadow:0 14px 38px #0f172a0c}.myai-image-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px}.myai-image-page textarea{width:100%;min-height:180px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:14px;padding:13px;font:inherit;resize:vertical}.myai-image-page select,.myai-image-page button{padding:10px 13px;border-radius:10px;border:1px solid #cbd5e1;font:inherit}.myai-image-page button{background:#1d4ed8;color:#fff;border:0;font-weight:800;cursor:pointer}.myai-image-result img{max-width:100%;border-radius:16px;border:1px solid #e2e8f0}.myai-muted{color:#64748b;font-size:13px;line-height:1.8}@media(max-width:800px){.myai-image-grid{grid-template-columns:1fr}.myai-nav .brand{width:100%;margin-left:0}.myai-settings-frame{height:calc(100vh - 210px);min-height:600px}}
</style>
"""


def _nav(path: str) -> str:
    def active(prefix: str) -> str:
        return " active" if path == prefix or path.startswith(prefix + "/") else ""

    return f"""
<nav class="myai-nav" id="myAiGlobalNav">
  <a class="brand" href="/">My-AI</a>
  <div class="group">
    <a class="{active('/')}" href="/">چت</a>
    <a class="{active('/learning')}" href="/learning">پیشرفت و یادگیری</a>
    <a class="{active('/image')}" href="/image">ساخت تصویر</a>
  </div>
  <span class="sep"></span>
  <div class="group">
    <a class="{active('/settings')}" href="/settings">تنظیمات</a>
    <a href="/settings-sections">بخش‌های تنظیمات</a>
    <a class="{active('/self-diagnostics')}" href="/self-diagnostics">گزارش سلامت</a>
    <a class="{active('/help')}" href="/help">راهنمای کامل</a>
  </div>
  <a class="myai-page-help" href="/help#assistant" target="_blank">راهنمای این صفحه</a>
</nav>
"""


def _settings_sections_page() -> str:
    sections = [
        ("github", "اتصال GitHub", "مدیریت اتصال، مخزن و احراز هویت GitHub"),
        ("update", "Self-Update", "بررسی و مدیریت به‌روزرسانی خودکار"),
        ("repair", "Self-Repair", "تنظیمات تعمیر خودکار و نیاز به تأیید"),
        ("learning", "یادگیری سریع", "تنظیمات سرعت، فاصله و تلاش‌های یادگیری"),
        ("resource", "منابع سیستم", "CPU، RAM، thread و GPU"),
        ("user", "کاربران", "مدیریت کاربران و وضعیت حساب‌ها"),
        ("permission", "مجوزها", "مجوزهای per-tool برای کاربران"),
        ("course", "آموزش‌های سفارشی", "ساخت و مدیریت دوره‌های یادگیری"),
        ("log", "لاگ‌ها", "سطح ثبت رویدادها و لاگ‌ها"),
        ("image", "ساخت تصویر", "تنظیمات موتور و سرویس تولید تصویر"),
    ]
    cards = "".join(
        f'<a class="myai-setting-link" href="/settings-section/{slug}"><b>{escape(title)}</b><span>{escape(desc)}</span></a>'
        for slug, title, desc in sections
    )
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>بخش‌های تنظیمات | My-AI</title>{NAV_STYLE}<style>body{{margin:0;background:#f3f4f6;color:#17202a}}.wrap{{max-width:1100px;margin:auto;padding:20px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}.myai-setting-link{{display:flex;flex-direction:column;gap:7px;padding:18px;background:#fff;border:1px solid #e5e7eb;border-radius:16px;text-decoration:none;color:#17202a;box-shadow:0 8px 24px #0f172a0b}}.myai-setting-link:hover{{border-color:#93c5fd;transform:translateY(-1px)}}.myai-setting-link span{{font-size:13px;color:#64748b;line-height:1.8}}</style></head><body><div class='wrap'>{_nav('/settings-sections')}<section class='card'><h1>بخش‌های تنظیمات</h1><p class='myai-muted'>هر بخش تنظیمات از اینجا در یک صفحه مستقل باز می‌شود و امکانات موجود پروژه را بدون حذف نگه می‌دارد.</p><div class='grid'>{cards}</div></section></div></body></html>"""


def _settings_section_page(slug: str) -> str:
    labels = {
        "github": "اتصال GitHub",
        "update": "Self-Update",
        "repair": "Self-Repair",
        "learning": "یادگیری سریع",
        "resource": "منابع سیستم",
        "user": "کاربران",
        "permission": "مجوزها",
        "course": "آموزش‌های سفارشی",
        "log": "لاگ‌ها",
        "image": "ساخت تصویر",
    }
    title = labels.get(slug, "تنظیمات")
    needle = json.dumps(title, ensure_ascii=False)
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{escape(title)} | تنظیمات My-AI</title>{NAV_STYLE}</head><body><div class='myai-settings-shell'>{_nav('/settings-section/'+slug)}<div class='card' style='padding:16px'><h1>{escape(title)}</h1><p class='myai-muted'>این صفحه فقط بخش «{escape(title)}» را از تنظیمات اصلی نمایش می‌دهد.</p><iframe id='settingsFrame' class='myai-settings-frame' src='/settings' title='{escape(title)}'></iframe></div></div><script>(function(){{var frame=document.getElementById('settingsFrame');frame.addEventListener('load',function(){{try{{var doc=frame.contentDocument||frame.contentWindow.document;var target={needle};var all=Array.from(doc.querySelectorAll('.card,section'));var found=null;all.forEach(function(el){{var h=el.querySelector('h1,h2,h3');if(h&&h.textContent.trim().toLowerCase().indexOf(target.toLowerCase())!==-1)found=el;}});if(found){{all.forEach(function(el){{if(el!==found&&el.querySelector('h1,h2,h3'))el.style.display='none';}});found.style.display='block';found.scrollIntoView({{block:'start'}});}}}}catch(e){{console.warn(e);}}}});}})();</script></body></html>"""


def _image_page() -> str:
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ساخت تصویر | My-AI</title>{NAV_STYLE}</head><body><main class='myai-image-page'>{_nav('/image')}<section class='myai-image-card'><h1>ساخت تصویر</h1><p class='myai-muted'>این صفحه مخصوص درخواست‌های تولید تصویر است. در صفحه چت اصلی تولید تصویر در دسترس نیست.</p><div class='myai-image-grid'><div><textarea id='imagePrompt' placeholder='توضیح دقیق تصویری که می‌خواهید ساخته شود...'></textarea><div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px'><select id='imageSize'><option value='1024x1024'>1024×1024</option><option value='1536x1024'>1536×1024</option><option value='1024x1536'>1024×1536</option></select><select id='imageQuality'><option value='high'>کیفیت بالا</option><option value='standard'>استاندارد</option></select><button id='generateImage'>ساخت تصویر</button></div><p id='imageStatus' class='myai-muted'></p></div><div id='imageResult' class='myai-image-result'></div></div></section></main><script>document.getElementById('generateImage').addEventListener('click',async function(){{var prompt=document.getElementById('imagePrompt').value.trim();var status=document.getElementById('imageStatus');var result=document.getElementById('imageResult');if(!prompt){{status.textContent='ابتدا درخواست تصویر را وارد کنید.';return}}this.disabled=true;status.textContent='در حال ساخت تصویر...';result.innerHTML='';try{{var r=await fetch('/image/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{prompt:prompt,size:document.getElementById('imageSize').value,quality:document.getElementById('imageQuality').value}})}});var j=await r.json();if(!r.ok)throw Error(j.detail||'خطا در تولید تصویر');result.innerHTML=j.url?'<img src="'+j.url+'" alt="'+prompt.replace(/"/g,'&quot;')+'"><p><a href="'+j.url+'" target="_blank">باز کردن تصویر</a></p>':'<pre>'+JSON.stringify(j,null,2)+'</pre>';status.textContent='تصویر آماده شد.'}}catch(e){{status.textContent='خطا: '+e.message}}finally{{this.disabled=false}}}});</script></body></html>"""


INJECT = NAV_STYLE + _nav("/") + """
<script id="myAiGlobalNavScript">
(function(){
  if(document.body && document.body.firstElementChild && document.body.firstElementChild.id==='myAiGlobalNav') return;
  var nav=document.getElementById('myAiGlobalNav');
  if(nav && document.body && nav.parentElement!==document.body && !document.querySelector('body>#myAiGlobalNav')) document.body.insertBefore(nav,document.body.firstChild);
  if(location.pathname==='/' && !window.__myAiPageGuards){
    window.__myAiPageGuards=true;
    function blocked(text){
      var s=String(text||'').toLowerCase().replace(/\s+/g,' ');
      return /(یاد بگیر|یادگیری را شروع|آموزش بده|learn this|teach yourself|start learning|ساخت تصویر|ساختن تصویر|بساز.*تصویر|تولید تصویر|generate image|create image|make an image)/i.test(s);
    }
    document.addEventListener('click',function(e){if(e.target&&e.target.closest&&e.target.closest('#sendBtn')){var box=document.getElementById('msg');if(box&&blocked(box.value)){e.preventDefault();e.stopImmediatePropagation();var m=document.getElementById('messages');if(m){var d=document.createElement('div');d.className='msgRow ai';d.innerHTML='<div class="msg"><div class="msgText">این درخواست در صفحه چت اصلی اجرا نمی‌شود. برای یادگیری به «پیشرفت و یادگیری» و برای ساخت تصویر به «ساخت تصویر» بروید.</div></div>';m.appendChild(d);m.scrollTop=m.scrollHeight}}}},true);
    document.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){var t=e.target;if(t&&t.id==='msg'&&blocked(t.value)){e.preventDefault();e.stopImmediatePropagation();var b=document.getElementById('sendBtn');if(b)b.click()}}},true);
  }
})();
</script>
"""


def install_ui_extensions(app) -> None:
    @app.get('/image', response_class=HTMLResponse)
    async def image_page():
        return HTMLResponse(_image_page(), headers={'Cache-Control':'no-store'})

    @app.get('/settings-sections', response_class=HTMLResponse)
    async def settings_sections_page():
        return HTMLResponse(_settings_sections_page(), headers={'Cache-Control':'no-store'})

    @app.get('/settings-section/{slug}', response_class=HTMLResponse)
    async def settings_section_page(slug: str):
        if slug not in {'github','update','repair','learning','resource','user','permission','course','log','image'}:
            return HTMLResponse(_settings_sections_page(), status_code=404)
        return HTMLResponse(_settings_section_page(slug), headers={'Cache-Control':'no-store'})

    @app.middleware('http')
    async def local_feature_ui(request, call_next):
        if request.method == 'POST' and request.url.path in {'/chat','/chat/stream'}:
            try:
                body = await request.body()
                payload = json.loads(body.decode('utf-8') or '{}')
                msg = str(payload.get('message') or '')
                low = re.sub(r'\s+', ' ', msg.lower())
                learning = re.search(r'(یاد بگیر|یادگیری را شروع|آموزش بده|learn this|teach yourself|start learning)', low)
                image = re.search(r'(ساخت تصویر|ساختن تصویر|بساز.*تصویر|تولید تصویر|generate image|create image|make an image)', low)
                if learning:
                    return JSONResponse({'answer':'این درخواست در صفحه چت اصلی اجرا نمی‌شود. برای آموزش و یادگیری به صفحه «پیشرفت و یادگیری» بروید.','redirect':'/learning'})
                if image:
                    return JSONResponse({'answer':'درخواست ساخت تصویر فقط در صفحه «ساخت تصویر» اجرا می‌شود.','redirect':'/image'})
            except Exception:
                pass
        response = await call_next(request)
        if not hasattr(response, 'body') or not response.body:
            return response
        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            return response
        if request.url.path in {'/login','/register'}:
            return response
        body = response.body.decode('utf-8', errors='replace')
        if 'id="myAiGlobalNav"' not in body:
            body = body.replace('<body>', '<body>' + INJECT, 1) if '<body>' in body else body.replace('</head>', NAV_STYLE + '</head>', 1).replace('</body>', INJECT + '</body>', 1)
        headers = {k: v for k, v in response.headers.items() if k.lower() not in {'content-length', 'content-type'}}
        return HTMLResponse(body, status_code=response.status_code, headers=headers)
