from __future__ import annotations

from html import escape


def _shell(title: str, body: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | My-AI</title>
<style>
body{{font-family:Tahoma,system-ui;background:#f5f7fb;color:#17202a;margin:0}}
main{{max-width:920px;margin:auto;padding:24px}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin:12px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
label{{display:block;font-weight:700;margin:8px 0}}input,select,textarea{{width:100%;box-sizing:border-box;padding:9px;border:1px solid #cbd5e1;border-radius:8px}}
button,a.button{{display:inline-block;border:0;border-radius:8px;padding:9px 14px;background:#1d4ed8;color:#fff;text-decoration:none;cursor:pointer;margin:4px 0}}
.muted{{color:#64748b}}pre{{white-space:pre-wrap;overflow:auto;background:#f8fafc;padding:10px;border-radius:8px}}
</style></head><body><main>
<p><a href="/settings">تنظیمات</a> · <a href="/">صفحه اصلی</a></p>
{body}
</main><script>{script}</script></body></html>"""


def index() -> str:
    cards = [
        ("MetaTrader 4/5", "اتصال، حساب، سرور، ترمینال، تست اتصال و داده بازار.", "/settings/ui/metatrader"),
        ("مدل و Provider", "Providerها، مدل‌ها و مسیر انتخاب مدل.", "/settings/providers"),
        ("یادگیری", "دوره‌ها، منابع و زمان‌بندی یادگیری.", "/learning"),
        ("امنیت", "Policy، نقش‌ها و مجوزهای ابزار.", "/settings/security-policies"),
        ("GitHub", "اتصال GitHub و تنظیمات repository.", "/settings/ui/github"),
        ("منابع سیستم", "CPU، RAM و تنظیمات اجرای مدل.", "/settings/ui/resources"),
        ("لاگ و مشاهده‌پذیری", "سطح لاگ و وضعیت مشاهده‌پذیری.", "/settings/ui/observability"),
        ("تنظیمات پیشرفته", "Registry، تاریخچه، import/export و کنترل‌های مدیریتی.", "/settings/ui/advanced"),
    ]
    body = "<h1>تنظیمات</h1><p class='muted'>هر حوزه یک فرم مستقل دارد؛ فرم‌ها فقط مسئول همان حوزه هستند.</p><div class='grid'>"
    for title, desc, href in cards:
        body += f"<section class='card'><h2>{escape(title)}</h2><p>{escape(desc)}</p><a class='button' href='{href}'>باز کردن</a></section>"
    body += "</div>"
    return _shell("تنظیمات", body)


def metatrader() -> str:
    fields = [
        ("domain.mt4mt5.version", "نسخه", "select"),
        ("domain.mt4mt5.install_path", "مسیر ترمینال", "text"),
        ("domain.mt4mt5.account", "حساب", "text"),
        ("domain.mt4mt5.password", "رمز عبور", "password"),
        ("domain.mt4mt5.server", "Broker Server", "text"),
        ("domain.mt4mt5.timeframe", "Timeframe پیش‌فرض", "text"),
    ]
    html = "<h1>MetaTrader 4/5</h1><p class='muted'>این فرم فقط تنظیمات اتصال و داده بازار را مدیریت می‌کند.</p><section class='card'><div class='grid'>"
    for key, label, kind in fields:
        if kind == "select":
            html += f"<label>{escape(label)}<select id='f-{escape(key)}'><option value='MT4'>MT4</option><option value='MT5'>MT5</option></select></label>"
        else:
            html += f"<label>{escape(label)}<input id='f-{escape(key)}' type='{kind}'></label>"
    html += """</div><button onclick="save()">ذخیره</button> <button onclick="test()">تست اتصال</button><pre id="out"></pre></section>
<section class="card"><h2>داده بازار</h2>
<label>Symbol<input id="symbol" value="EURUSD"></label>
<button onclick="quote()">Quote</button>
<button onclick="bars()">Bars</button>
<pre id="market"></pre></section>"""
    script = r"""
async function req(u,o){let r=await fetch(u,o);let t=await r.text();let j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||j.message||t);return j}
const keys=["domain.mt4mt5.version","domain.mt4mt5.install_path","domain.mt4mt5.account","domain.mt4mt5.password","domain.mt4mt5.server","domain.mt4mt5.timeframe"];
async function load(){let j=await req("/settings/registry");let m=Object.fromEntries(j.items.map(x=>[x.key,x]));keys.forEach(k=>{let e=document.getElementById("f-"+k);if(e)e.value=m[k]?.value||""})}
async function save(){try{for(const k of keys){let e=document.getElementById("f-"+k);if(!e)continue;await req("/settings/registry/"+encodeURIComponent(k),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({value:e.value})})}out.textContent="تنظیمات ذخیره شد."}catch(e){out.textContent=e.message}}
async function test(){try{out.textContent=JSON.stringify(await req("/settings/mt4mt5/test"),null,2)}catch(e){out.textContent=e.message}}
async function quote(){try{market.textContent=JSON.stringify(await req("/settings/mt4mt5/quote?symbol="+encodeURIComponent(symbol.value)),null,2)}catch(e){market.textContent=e.message}}
async function bars(){try{market.textContent=JSON.stringify(await req("/settings/mt4mt5/bars?symbol="+encodeURIComponent(symbol.value)+"&count=100"),null,2)}catch(e){market.textContent=e.message}}
load()
"""
    return _shell("MetaTrader 4/5", html, script)


def github() -> str:
    body = """<h1>GitHub</h1><p class='muted'>این فرم فقط اتصال GitHub را مدیریت می‌کند.</p>
<section class='card'><label>API URL<input id='api'></label>
<label>Repository<input id='repo' placeholder='owner/repository'></label>
<label>Username<input id='user'></label>
<button onclick='save()'>ذخیره</button><pre id='out'></pre></section>"""
    script = r"""
async function req(u,o){let r=await fetch(u,o);let t=await r.text();let j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||j.message||t);return j}
async function load(){let j=await req("/settings/config");api.value=j.github?.api_url||"";repo.value=j.github?.repository||"";user.value=j.github?.username||""}
async function save(){try{await req("/settings/github",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({api_url:api.value.trim(),repository:repo.value.trim(),username:user.value.trim()})});out.textContent="تنظیمات GitHub ذخیره شد."}catch(e){out.textContent=e.message}}
load()
"""
    return _shell("GitHub", body, script)


def advanced() -> str:
    body = """<h1>تنظیمات پیشرفته</h1><p class='muted'>عملیات مدیریتی در صفحات مستقل انجام می‌شوند.</p>
<div class='grid'>
<section class='card'><h2>Registry</h2><p>مشاهده و تغییر تنظیمات ثبت‌شده.</p><a class='button' href='/settings/registry'>باز کردن Registry</a></section>
<section class='card'><h2>History</h2><p>تاریخچه تغییرات تنظیمات.</p><a class='button' href='/settings/registry/history'>باز کردن History</a></section>
<section class='card'><h2>Import / Export</h2><p>انتقال تنظیمات با کنترل دسترسی administrator.</p><a class='button' href='/settings/registry/export'>Export</a></section>
</div>"""
    return _shell("تنظیمات پیشرفته", body)


def simple(title: str, description: str, endpoint: str, keys: list[tuple[str, str]]) -> str:
    fields = "".join(
        f"<label>{escape(label)}<input id='f-{escape(key)}'></label>" for key, label in keys
    )
    script = f"""
async function req(u,o){{let r=await fetch(u,o);let t=await r.text();let j={{}};try{{j=JSON.parse(t)}}catch(_){{j={{detail:t}}}}if(!r.ok)throw Error(j.detail||j.message||t);return j}}
async function load(){{let j=await req("/settings/registry");let m=Object.fromEntries(j.items.map(x=>[x.key,x]));{''.join(f'document.getElementById("f-{key}").value=m["{key}"]?.value||"";' for key,_ in keys)}}}
async function save(){{try{{{''.join(f'await req("/settings/registry/{key}",{{method:"PUT",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{value:document.getElementById("f-{key}").value}})}});' for key,_ in keys)}out.textContent="ذخیره شد."}}catch(e){{out.textContent=e.message}}}}
load()
"""
    return _shell(title, f"<h1>{escape(title)}</h1><p class='muted'>{escape(description)}</p><section class='card'><div class='grid'>{fields}</div><button onclick='save()'>ذخیره</button><pre id='out'></pre></section>", script)
