from html import escape
from .shell import shell

def simple(title: str, description: str, endpoint: str, keys: list[tuple[str, str]]) -> str:
    del endpoint
    fields = "".join(f"<label>{escape(label)}<input id='f-{escape(key)}'></label>" for key,label in keys)
    loads = "".join(f'document.getElementById("f-{key}").value=m["{key}"]?.value||"";' for key,_ in keys)
    saves = "".join(f'await req("/settings/registry/{key}",{{method:"PUT",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{value:document.getElementById("f-{key}").value}})}});' for key,_ in keys)
    script = f"""async function req(u,o){{let r=await fetch(u,o),t=await r.text(),j={{}};try{{j=JSON.parse(t)}}catch(_){{j={{detail:t}}}}if(!r.ok)throw Error(j.detail||j.message||t);return j}}
async function load(){{let j=await req("/settings/registry"),m=Object.fromEntries(j.items.map(x=>[x.key,x]));{loads}}}
async function save(){{try{{{saves}out.textContent="ذخیره شد."}}catch(e){{out.textContent=e.message}}}}
load()"""
    body = f"<h1>{escape(title)}</h1><p class='muted'>{escape(description)}</p><section class='card'><div class='grid'>{fields}</div><button onclick='save()'>ذخیره</button><pre id='out'></pre></section>"
    return shell(title, body, script)
