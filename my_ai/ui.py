from __future__ import annotations

from pathlib import Path


HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"


CHAT_RUNTIME_PATCH = r"""
<script id="myAiChatRuntimePatch">
(function(){
'use strict';
var sid=null, busy=false;
function el(id){return document.getElementById(id)}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;')}
function message(text, role){var box=el('messages');if(!box)return;var row=document.createElement('div');row.className='msgRow '+(role==='user'?'user':'ai');var bubble=document.createElement('div');bubble.className='msg';var body=document.createElement('div');body.className='msgText';body.textContent=String(text==null?'':text);bubble.appendChild(body);row.appendChild(bubble);box.appendChild(row)}
function render(items){var box=el('messages');if(!box)return;box.innerHTML='';(Array.isArray(items)?items:[]).forEach(function(x){message(x.content??x.message??x.text??'',String(x.role||'assistant').toLowerCase()==='user'?'user':'ai')});box.scrollTop=box.scrollHeight}
async function json(url,opt){var r=await fetch(url,Object.assign({cache:'no-store'},opt||{}));var t=await r.text(),j={};try{j=JSON.parse(t)}catch(_){j={detail:t}}if(!r.ok)throw Error(j.detail||('HTTP '+r.status));return j}
async function sessions(){var j=await json('/chat/sessions?x='+Date.now());return Array.isArray(j.sessions)?j.sessions:[]}
function markActive(){document.querySelectorAll('[data-chat-id]').forEach(function(b){b.classList.toggle('active',Number(b.getAttribute('data-chat-id'))===Number(sid))})}
async function loadSession(id){id=Number(id);if(!Number.isFinite(id)||id<=0)return;sid=id;markActive();try{var j=await json('/chat/history?session_id='+encodeURIComponent(id)+'&limit=200');render(j.messages||[]);markActive()}catch(e){render([{role:'assistant',content:'خطا در بارگذاری گفتگو: '+e.message}])}}
async function refreshList(selectFirst){var list=await sessions();var box=el('chatList');if(!box)return;box.innerHTML='';list.forEach(function(s){var row=document.createElement('div');row.className='chatRow';var b=document.createElement('button');b.type='button';b.className='chatItem'+(Number(s.id)===Number(sid)?' active':'');b.setAttribute('data-chat-id',s.id);b.textContent=(s.pinned?'📌 ':'')+(s.title||'گفتگوی جدید');row.appendChild(b);box.appendChild(row)});if(selectFirst&&sid==null&&list.length)await loadSession(Number(list[0].id));else markActive()}
async function sendMessage(){if(busy)return;var input=el('msg');if(!input)return;var text=input.value.trim();if(!text)return;busy=true;var send=el('sendBtn');if(send)send.disabled=true;try{message(text,'user');input.value='';var j=await json('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,session_id:sid})});if(j.session_id!=null)sid=Number(j.session_id);message(j.answer||j.message||'','ai');await refreshList(false);markActive()}catch(e){message('خطا: '+e.message,'ai')}finally{busy=false;if(send)send.disabled=false}}
async function newSession(){try{var j=await json('/chat/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'گفتگوی جدید'})});sid=Number(j.id||j.session_id);render([]);await refreshList(false);markActive();var input=el('msg');if(input)input.focus()}catch(e){message('خطا در ایجاد گفتگوی جدید: '+e.message,'ai')}}
document.addEventListener('click',function(e){var chat=e.target.closest&&e.target.closest('[data-chat-id]');if(chat){e.preventDefault();e.stopImmediatePropagation();loadSession(Number(chat.getAttribute('data-chat-id')));return}var n=e.target.closest&&e.target.closest('#newChat');if(n){e.preventDefault();e.stopImmediatePropagation();newSession();return}var s=e.target.closest&&e.target.closest('#sendBtn');if(s){e.preventDefault();e.stopImmediatePropagation();sendMessage();return}},true);
document.addEventListener('keydown',function(e){if(e.target&&e.target.id==='msg'&&e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.stopImmediatePropagation();sendMessage()}},true);
window.addEventListener('load',function(){refreshList(true).catch(function(e){var box=el('chatList');if(box)box.textContent='خطا: '+e.message})});
})();
</script>
"""


def page() -> str:
    html = HTML_PATH.read_text(encoding="utf-8")
    return html.replace("</body>", CHAT_RUNTIME_PATCH + "</body>")


HTML = page()
