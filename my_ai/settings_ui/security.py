from .shell import shell

def indicators() -> str:
    body = """<h1>Indicators</h1><p class='muted'>مدیریت چرخه تولید، compile، install و readback indicator.</p>
<section class='card'><label>Platform<select id='platform'><option>MT4</option><option>MT5</option></select></label>
<label>Source<textarea id='source' rows='10'></textarea></label><label>Source path<input id='path'></label>
<button onclick='compileIt()'>Compile</button><button onclick='installIt()'>Install</button><pre id='out'></pre></section>"""
    script = r"""async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||t);return j}
async function compileIt(){try{out.textContent=JSON.stringify(await req("/settings/mt4mt5/indicator/compile",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_path:path.value,platform:platform.value})}),null,2)}catch(e){out.textContent=e.message}}
async function installIt(){try{out.textContent=JSON.stringify(await req("/settings/mt4mt5/indicator/install",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_path:path.value,platform:platform.value})}),null,2)}catch(e){out.textContent=e.message}}"""
    return shell("Indicators", body, script)

def permissions() -> str:
    body = """<h1>Tools & Permissions</h1><p class='muted'>مجوزهای MetaTrader به read، install/write و trade تفکیک شده‌اند.</p>
<section class='card'><label><input id='read' type='checkbox'> MetaTrader read</label>
<label><input id='install' type='checkbox'> MetaTrader install/write</label>
<label><input id='trade' type='checkbox'> MetaTrader trade</label>
<button onclick='save()'>ذخیره</button><pre id='out'></pre></section>"""
    script = r"""async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||t);return j}
async function load(){let j=await req("/settings/registry"),m=Object.fromEntries(j.items.map(x=>[x.key,x]));read.value=m["security.metatrader_read"]?.value==="true";install.value=m["security.metatrader_install"]?.value==="true";trade.value=m["security.metatrader_trade"]?.value==="true"} async function save(){try{for(const [k,e] of [["security.metatrader_read",read],["security.metatrader_install",install],["security.metatrader_trade",trade]])await req("/settings/registry/"+encodeURIComponent(k),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({value:e.checked?"true":"false"})});out.textContent="ذخیره شد."}catch(e){out.textContent=e.message}} load()"""
    return shell("Tools & Permissions", body, script)
