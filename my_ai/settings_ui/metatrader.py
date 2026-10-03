from html import escape
from .shell import shell

def metatrader() -> str:
    fields = [
        ("domain.mt4mt5.version", "نسخه", "select"),
        ("domain.mt4mt5.install_path", "مسیر ترمینال", "text"),
        ("domain.mt4mt5.account", "حساب", "text"),
        ("domain.mt4mt5.password", "رمز عبور", "password"),
        ("domain.mt4mt5.server", "Broker Server", "text"),
        ("domain.mt4mt5.timeframe", "Timeframe پیش‌فرض", "select"),
    ]
    html = "<h1>MetaTrader 4/5</h1><p class='muted'>این فرم فقط اتصال و داده بازار را مدیریت می‌کند.</p><section class='card'><div class='grid'>"
    for key,label,kind in fields:
        if kind == "select" and key.endswith(".version"):
            control = "<select id='f-domain.mt4mt5.version'><option value='MT4'>MT4</option><option value='MT5'>MT5</option></select>"
        elif kind == "select":
            control = "<select id='f-domain.mt4mt5.timeframe'>" + "".join(f"<option>{x}</option>" for x in ("M1","M5","M15","M30","H1","H4","D1")) + "</select>"
        else:
            control = f"<input id='f-{escape(key)}' type='{kind}'>"
        html += f"<label>{escape(label)}{control}</label>"
    html += """</div><button onclick="save()">ذخیره</button> <button onclick="testConnection()">تست اتصال</button><pre id="out"></pre></section>
<section class="card"><h2>داده بازار</h2><label>Symbol<input id="symbol" value="EURUSD"></label>
<button onclick="quote()">Quote</button><button onclick="bars()">Bars</button><pre id="market"></pre></section>"""
    script = r"""
async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||j.message||t);return j}
const keys=["domain.mt4mt5.version","domain.mt4mt5.install_path","domain.mt4mt5.account","domain.mt4mt5.password","domain.mt4mt5.server","domain.mt4mt5.timeframe"];
async function load(){let j=await req("/settings/registry"),m=Object.fromEntries(j.items.map(x=>[x.key,x]));keys.forEach(k=>{let e=document.getElementById("f-"+k);if(e)e.value=m[k]?.value||""})}
async function save(){try{for(const k of keys){let e=document.getElementById("f-"+k);await req("/settings/registry/"+encodeURIComponent(k),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({value:e.value})})}out.textContent="تنظیمات ذخیره شد."}catch(e){out.textContent=e.message}}
async function testConnection(){try{out.textContent=JSON.stringify(await req("/settings/mt4mt5/test"),null,2)}catch(e){out.textContent=e.message}}
async function quote(){try{market.textContent=JSON.stringify(await req("/settings/mt4mt5/quote?symbol="+encodeURIComponent(symbol.value)),null,2)}catch(e){market.textContent=e.message}}
async function bars(){try{market.textContent=JSON.stringify(await req("/settings/mt4mt5/bars?symbol="+encodeURIComponent(symbol.value)+"&count=100"),null,2)}catch(e){market.textContent=e.message}}
load()
"""
    return shell("MetaTrader 4/5", html, script)
