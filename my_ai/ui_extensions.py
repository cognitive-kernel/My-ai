from __future__ import annotations

from fastapi.responses import HTMLResponse


INJECT = r"""
<div class="card" id="localFileTools" style="margin-top:12px">
  <b>فایل و پردازش محلی</b>
  <input id="chatFile" type="file" style="display:block;margin:8px 0" />
  <span class="small">فایل انتخاب‌شده هنگام ارسال در فضای محلی برنامه ذخیره و برای تحلیل به My-AI داده می‌شود.</span>
  <div id="fileStatus" class="small"></div>
</div>
<script>
(function(){
  if(window.__myAiFeatureExtensions)return;
  window.__myAiFeatureExtensions=true;
  var box=document.getElementById('localFileTools'),msg=document.getElementById('msg');
  if(box&&msg&&msg.parentNode)msg.parentNode.insertBefore(box,msg);
  async function uploadAndAnalyze(){
    var input=document.getElementById('chatFile');
    if(!input||!input.files||!input.files.length)return null;
    var fd=new FormData();fd.append('file',input.files[0]);
    var status=document.getElementById('fileStatus');status.textContent='در حال بارگذاری و تحلیل فایل...';
    var r=await fetch('/files/upload',{method:'POST',body:fd});
    var j=await r.json();if(!r.ok)throw Error(j.detail||'خطای بارگذاری فایل');
    var a=await fetch('/files/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:j.path})});
    var aj=await a.json();if(!a.ok)throw Error(aj.detail||'خطای تحلیل فایل');
    status.textContent='فایل آماده شد: '+j.path;input.value='';return aj;
  }
  var oldSend=window.myAiSend;
  window.myAiSend=async function(){
    var input=document.getElementById('chatFile');
    if(input&&input.files&&input.files.length){
      try{
        var analysis=await uploadAndAnalyze();
        var current=document.getElementById('msg');
        var extra='\n\n[Attached local file analysis]\n'+JSON.stringify(analysis,null,2);
        current.value=(current.value||'')+extra;
      }catch(e){var s=document.getElementById('fileStatus');if(s)s.textContent='خطا: '+e.message;return}
    }
    return oldSend.apply(this,arguments);
  };
  async function control(language,action){
    var r=await fetch('/learning/'+encodeURIComponent(language)+'/'+action,{method:'POST'}),j=await r.json();
    if(!r.ok)throw Error(j.detail||'خطا');
    return j;
  }
  async function addControls(){
    var dash=document.getElementById('dashboard');if(!dash)return;
    dash.querySelectorAll('details').forEach(function(d){
      if(d.querySelector('.learning-controls'))return;
      var summary=d.querySelector('summary');if(!summary)return;
      var text=summary.textContent||'';
      var language=text.split('·')[0].trim();if(!language)return;
      var box=document.createElement('div');box.className='learning-controls';box.style.marginTop='8px';
      var stop=document.createElement('button');stop.type='button';stop.textContent='متوقف کردن یادگیری';
      var resume=document.createElement('button');resume.type='button';resume.textContent='ادامه یادگیری';
      stop.onclick=async function(){try{await control(language,'stop');setTimeout(addControls,100)}catch(e){alert(e.message)}};
      resume.onclick=async function(){try{await control(language,'resume');setTimeout(addControls,100)}catch(e){alert(e.message)}};
      box.appendChild(stop);box.appendChild(resume);d.appendChild(box);
    });
  }
  setInterval(addControls,1000);
  setTimeout(addControls,100);
})();
</script>
"""


def install_ui_extensions(app) -> None:
    @app.middleware("http")
    async def local_feature_ui(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not hasattr(response, "body") or not response.body:
            return response
        body = response.body.decode("utf-8", errors="replace")
        if "id=\"localFileTools\"" in body:
            return response
        body = body.replace("</body>", INJECT + "</body>")
        headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "content-type"}}
        return HTMLResponse(body, status_code=response.status_code, headers=headers)
