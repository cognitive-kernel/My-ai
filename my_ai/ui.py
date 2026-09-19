HTML="""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>My-AI</title><style>
body{font-family:Tahoma,system-ui;margin:0;background:#f3f4f6;color:#17202a}main{max-width:1100px;margin:auto;padding:20px}.card{background:#fff;padding:18px;border-radius:14px;margin:12px 0}button,select{padding:10px 15px;border:0;border-radius:9px;cursor:pointer;margin:3px}textarea{width:100%;box-sizing:border-box;padding:12px;margin:8px 0;border:1px solid #ccc;border-radius:9px}#messages{height:400px;overflow:auto;background:#f8fafc;padding:10px}.msg{padding:9px;margin:7px;border-radius:9px;white-space:pre-wrap}.user{background:#dbeafe}.ai{background:#e5e7eb}pre{white-space:pre-wrap;background:#111827;color:#fff;padding:12px;direction:ltr;text-align:left;overflow:auto}.bar{height:24px;background:#ddd;border-radius:8px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.small{font-size:13px;color:#5b6470}.danger{background:#fee2e2}.helpBtn{font-size:13px;background:#e0e7ff;color:#1e3a8a;text-decoration:none;padding:6px 10px;border-radius:7px;float:left}.ok{background:#dcfce7}button:disabled{opacity:.55;cursor:not-allowed}</style></head><body><main>
<h1>My-AI <a class='helpBtn' href='/help#chat' target='_blank'>راهنمای کامل</a></h1><p id='subtitle'>دستیار محلی برای یادگیری، برنامه‌نویسی و بررسی امنیتی</p>
<div class='card'><button id='faBtn' type='button'>فارسی</button><button id='enBtn' type='button'>English</button><select id='voiceLang'><option value='fa-IR'>صدای فارسی</option><option value='en-US'>English voice</option></select></div>
<div class='card'><h2 id='chatTitle'>دستور به دستیار <a class='helpBtn' href='/help#chat' target='_blank'>راهنما</a></h2><div id='messages'></div><textarea id='msg' rows='3' placeholder='مثلاً: پایتون یاد بگیر، بعد یک صفحه ورود بساز و پن‌تست بگیر' onkeydown='if(event.key==="Enter"&&!event.ctrlKey&&!event.shiftKey){event.preventDefault();window.myAiSend();}'></textarea><button type='button' id='sendBtn' onclick='window.myAiSend()'>ارسال</button><button type='button' id='voiceBtn'>گفتار</button><button type='button' id='stopBtn'>توقف صدا</button><p class='small' id='policy'>پیش‌فرض: «پن‌تست» یعنی بررسی و اصلاح. اگر بگویید «فقط گزارش بده» یا «فقط تست بگیر»، فقط گزارش می‌شود. دستور صریح شما همیشه بر پیش‌فرض غلبه دارد.</p></div>
<div class='card'><h2 id='progressTitle'>پیشرفت یادگیری <a class='helpBtn' href='/help#learning' target='_blank'>راهنما</a></h2><div id='dashboard'>در حال بارگذاری...</div></div>
<div class='card'><h2 id='securityTitle'>گزارش امنیتی <a class='helpBtn' href='/help#security' target='_blank'>راهنما</a></h2><div class='grid'><div class='card ok'><b>اصلاح خودکار</b><p>با درخواست صریح شما فعال می‌شود یا طبق پیش‌فرض پن‌تست.</p></div><div class='card danger'><b>گزارش فقط</b><p>با «فقط تست بگیر» یا «فقط گزارش بده» هیچ تغییری در پروژه ایجاد نمی‌شود.</p></div></div></div>
<div class='card'><h2 id='learnTitle'>یادگیری سریع <a class='helpBtn' href='/help#learning' target='_blank'>راهنما</a></h2><button type='button' data-learn='Python'>Python</button><button type='button' data-learn='PHP'>PHP</button><button type='button' data-learn='JavaScript'>JavaScript</button><button type='button' data-learn='Pentest'>Pentest</button><pre id='learnout'></pre></div>
<script>
window.myAiSend=window.myAiSend||async function(){
  var el=document.getElementById('msg');
  if(!el)return;
  var m=(el.value||'').trim();
  if(!m)return;
  el.value='';
  var box=document.getElementById('messages');
  if(box){box.insertAdjacentHTML('beforeend','<div class="msg user"></div>');box.lastElementChild.textContent=m;}
  try{
    var r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
    var t=await r.text();
    var j;try{j=JSON.parse(t)}catch(e){j={answer:t}}
    if(box){box.insertAdjacentHTML('beforeend','<div class="msg ai"></div>');box.lastElementChild.textContent=j.answer||JSON.stringify(j);box.scrollTop=box.scrollHeight;}
  }catch(e){
    if(box){box.insertAdjacentHTML('beforeend','<div class="msg ai"></div>');box.lastElementChild.textContent='خطا: '+e.message;}
  }
};
</script>
<script>
(function(){
'use strict';
var recognition=null,voiceLocale='fa-IR',uiLang='fa',busy=false;
var T={fa:{sub:'دستیار محلی برای یادگیری، برنامه‌نویسی و بررسی امنیتی',chat:'دستور به دستیار',send:'ارسال',voice:'گفتار',stop:'توقف صدا',progress:'پیشرفت یادگیری',security:'گزارش امنیتی',learn:'یادگیری سریع',ph:'مثلاً: پایتون یاد بگیر، بعد یک صفحه ورود بساز و پن‌تست بگیر',policy:'پیش‌فرض: «پن‌تست» یعنی بررسی و اصلاح. اگر بگویید «فقط گزارش بده» یا «فقط تست بگیر»، فقط گزارش می‌شود. دستور صریح شما همیشه بر پیش‌فرض غلبه دارد.'},en:{sub:'Local assistant for learning, programming and security testing',chat:'Command the assistant',send:'Send',voice:'Voice',stop:'Stop voice',progress:'Learning progress',security:'Security report',learn:'Quick learning',ph:'Example: learn Python, then build a login page and pentest it',policy:'Default: “pentest” means test and remediate. If you say “report only” or “test only”, it only reports. Your explicit command always overrides the default.'}};
function $(id){return document.getElementById(id)}
function add(t,w){var d=document.createElement('div');d.className='msg '+w;d.textContent=t;$('messages').appendChild(d);$('messages').scrollTop=$('messages').scrollHeight}
function setLang(l){uiLang=l;document.documentElement.lang=l;document.documentElement.dir=l==='fa'?'rtl':'ltr';var t=T[l];$('subtitle').textContent=t.sub;$('chatTitle').firstChild.textContent=t.chat;$('sendBtn').textContent=t.send;$('voiceBtn').textContent=t.voice;$('stopBtn').textContent=t.stop;$('progressTitle').firstChild.textContent=t.progress;$('securityTitle').firstChild.textContent=t.security;$('learnTitle').firstChild.textContent=t.learn;$('msg').placeholder=t.ph;$('policy').textContent=t.policy}
async function post(p,b){var r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});var text=await r.text();var j;try{j=JSON.parse(text)}catch(_){throw Error('HTTP '+r.status+': '+text.slice(0,300))}if(!r.ok)throw Error(j.detail||'HTTP '+r.status);return j}
function renderResult(j){var a=j.answer||'';if(j.type==='code'&&j.data)a+='\n\n'+(j.data.code||'');if(j.type==='security'&&j.data){a+='\n\n';a+=(uiLang==='fa'?'خلاصه: ':'Summary: ')+JSON.stringify(j.data.summary||{});(j.data.findings||[]).forEach(function(f){a+='\n['+f.severity+'] '+f.title+' — '+(f.file||'')+':'+(f.line||'')+'\n'+(uiLang==='fa'?'راهکار: ':'Fix: ')+(f.remediation||'')})}if(j.type==='learning'&&j.data)a+='\n'+JSON.stringify(j.data);return a||JSON.stringify(j,null,2)}
async function send(){if(busy)return;var m=$('msg').value.trim();if(!m)return;busy=true;$('sendBtn').disabled=true;add(m,'user');$('msg').value='';try{var j=await post('/chat',{message:m});var a=renderResult(j);add(a,'ai');speak(a);loadDash()}catch(e){add('خطا: '+(e.message||String(e)),'ai')}finally{busy=false;$('sendBtn').disabled=false;$('msg').focus()}}
function voiceInput(){var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){add(uiLang==='fa'?'تشخیص گفتار در این مرورگر پشتیبانی نمی‌شود.':'Speech Recognition is not supported in this browser.','ai');return}recognition=new SR();recognition.lang=voiceLocale;recognition.interimResults=false;recognition.onresult=function(e){$('msg').value=e.results[0][0].transcript;send()};recognition.onerror=function(e){add('Voice error: '+e.error,'ai')};recognition.start()}
function stopVoice(){if(recognition)recognition.stop();if(window.speechSynthesis)speechSynthesis.cancel()}
function speak(t){if(window.speechSynthesis){speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(t);u.lang=voiceLocale;speechSynthesis.speak(u)}}
async function loadHistory(){try{var r=await fetch('/chat/history?limit=100',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);var j=await r.json();$('messages').innerHTML='';(j.messages||[]).forEach(function(x){add(x.content,x.role==='user'?'user':'ai')})}catch(e){console.error(e)}}
async function learn(lang){$('learnout').textContent='در حال مطالعه '+lang+'... این مرحله ممکن است چند دقیقه زمان ببرد.';try{var j=await post('/learning/step',{language:lang});$('learnout').textContent=JSON.stringify(j,null,2);loadDash()}catch(e){$('learnout').textContent='خطا: '+(e.message||String(e));loadDash()}}
async function loadDash(){try{var r=await fetch('/learning/status');var j=await r.json(),rows=j.languages||[],h='<table style="width:100%"><tr><th>زبان / Language</th><th>موضوعات</th><th>درصد</th><th>میانگین</th></tr>';rows.forEach(function(x){h+='<tr><td>'+x.language+'</td><td>'+x.completed_topics+'/'+x.total_topics+'</td><td>'+x.progress_percent+'%<div class="bar"><div class="fill" style="width:'+x.progress_percent+'%">'+x.progress_percent+'%</div></div></td><td>'+x.average_score+'%</td></tr>'});h+='</table>';$('dashboard').innerHTML=h}catch(e){$('dashboard').textContent='خطا: '+(e.message||String(e))}}
function init(){
$('faBtn').addEventListener('click',function(){setLang('fa')});$('enBtn').addEventListener('click',function(){setLang('en')});$('voiceLang').addEventListener('change',function(){voiceLocale=this.value});$('voiceBtn').addEventListener('click',voiceInput);$('stopBtn').addEventListener('click',stopVoice);document.querySelectorAll('[data-learn]').forEach(function(b){b.addEventListener('click',function(){learn(this.getAttribute('data-learn'))})});setLang('fa');loadHistory();loadDash();$('msg').focus()}
window.myAiSend=send;if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
</script></main></body></html>"""
def page(): return HTML
