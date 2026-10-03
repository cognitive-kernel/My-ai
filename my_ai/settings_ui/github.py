from .shell import shell

def github() -> str:
    body = """<h1>GitHub</h1><p class='muted'>این فرم فقط اتصال GitHub را مدیریت می‌کند.</p>
<section class='card'><label>API URL<input id='api'></label>
<label>Repository<input id='repo' placeholder='owner/repository'></label>
<label>Username<input id='user'></label>
<button onclick='save()'>ذخیره</button><pre id='out'></pre></section>"""
    script = r"""
async function req(u,o){let r=await fetch(u,o),t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||j.message||t);return j}
async function load(){let j=await req("/settings/config");api.value=j.github?.api_url||"";repo.value=j.github?.repository||"";user.value=j.github?.username||""}
async function save(){try{await req("/settings/github",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({api_url:api.value.trim(),repository:repo.value.trim(),username:user.value.trim()})});out.textContent="تنظیمات GitHub ذخیره شد."}catch(e){out.textContent=e.message}}
load()
"""
    return shell("GitHub", body, script)
