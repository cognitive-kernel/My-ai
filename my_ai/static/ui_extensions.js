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
  async function generateFile(){
    var prompt=document.getElementById('fileGeneratePrompt').value.trim();
    var format=document.getElementById('fileGenerateFormat').value;
    var status=document.getElementById('fileStatus');
    if(!prompt){status.textContent='ابتدا توضیح ساخت فایل را وارد کنید.';return}
    status.textContent='در حال ساخت فایل...';
    var filename='myai-generated-'+Date.now()+'.'+format;
    var r=await fetch('/files/generate/from-chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt,format:format,filename:filename})});
    var j=await r.json();if(!r.ok)throw Error(j.detail||'خطای ساخت فایل');
    status.textContent='فایل ساخته شد: '+j.local_path;
  }
  var gen=document.getElementById('fileGenerateButton');
  if(gen)gen.onclick=function(){generateFile().catch(function(e){document.getElementById('fileStatus').textContent='خطا: '+e.message})};
  var oldSend=window.myAiSend;
  if(typeof oldSend==='function')window.myAiSend=async function(){
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
})();
