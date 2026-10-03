from .shell import shell

def resources() -> str:
    body = """<h1>منابع سیستم</h1><section class='card'>
<label>CPU %<input id='cpu'></label><label>CPU threads<input id='threads'></label>
<label>RAM %<input id='ram'></label><label>GPU layers<input id='gpu'></label>
<button onclick='save()'>ذخیره</button><pre id='out'></pre></section>"""
    script = r"""async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||t);return j}
async function load(){let j=await req("/settings/config");cpu.value=j.resources.cpu_percent;threads.value=j.resources.cpu_threads;ram.value=j.resources.ram_percent;gpu.value=j.resources.gpu_layers} 
async function save(){try{let j=await req("/settings/resources",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({cpu_percent:Number(cpu.value),cpu_threads:Number(threads.value),ram_percent:Number(ram.value),gpu_layers:Number(gpu.value)})});out.textContent=JSON.stringify(j,null,2)}catch(e){out.textContent=e.message}} load()"""
    return shell("منابع سیستم", body, script)

def observability() -> str:
    body = """<h1>مشاهده‌پذیری</h1><section class='card'>
<label>Log level<select id='level'><option>DEBUG</option><option>INFO</option><option>WARNING</option><option>ERROR</option><option>CRITICAL</option></select></label>
<button onclick='save()'>ذخیره</button><button onclick='metrics()'>Metrics</button><pre id='out'></pre></section>"""
    script = r"""async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||t);return j}
async function load(){let j=await req("/settings/config");level.value=j.logging.level} async function save(){try{await req("/settings/logging",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({level:level.value})});out.textContent="ذخیره شد."}catch(e){out.textContent=e.message}} async function metrics(){try{out.textContent=JSON.stringify(await req("/settings/metrics"),null,2)}catch(e){out.textContent=e.message}} load()"""
    return shell("مشاهده‌پذیری", body, script)
