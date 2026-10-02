function registryInput(x){
  var key=esc(x.key), value=esc(x.value), type=x.type==="int"||x.type==="float"?"number":"text";
  var step=x.type==="float"?"any":"1";
  var attrs=type==="number"?" type=\"number\" step=\""+step+"\"":" type=\"text\"";
  return "<input id=\"reg-"+key+"\""+attrs+" value=\""+value+"\" style=\"max-width:220px\">";
}
async function updateRegisteredSetting(key){
  try{
    var meta=(await req("/settings/registry")).items.find(function(x){return x.key===key});
    var raw=byId("reg-"+key).value, value=meta.type==="int"?Number.parseInt(raw,10):meta.type==="float"?Number.parseFloat(raw):raw;
    var j=await req("/settings/registry/"+encodeURIComponent(key),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({value:value})});
    setText("registryout","تنظیم "+key+" ذخیره شد: "+j.value); await loadRegistry();
  }catch(e){setText("registryout","خطا: "+e.message)}
}
async function exportRegistry(){
  try{
    var j=await req("/settings/registry/export");
    var blob=new Blob([JSON.stringify(j,null,2)],{type:"application/json"});
    var a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="my-ai-settings-v"+j.version+".json";a.click();URL.revokeObjectURL(a.href);
    setText("registryout","خروجی تنظیمات ایجاد شد.");
  }catch(e){setText("registryout","خطا: "+e.message)}
}
async function importRegistryFile(file){
  if(!file)return;
  try{
    var text=await file.text(), payload=JSON.parse(text);
    var j=await req("/settings/registry/import",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    setText("registryout","تنظیمات وارد شد: "+j.imported);await loadSettings();await loadRegistry();
  }catch(e){setText("registryout","خطا: "+e.message)}
}
async function loadRegistry(){
  var box=byId("settings-registry");if(!box)return;
  try{
    var j=await req("/settings/registry");
    box.innerHTML=(j.items||[]).map(function(x){
      var choices=x.choices||[];
      var editor=choices.length?"<select id=\"reg-"+esc(x.key)+"\">"+choices.map(function(v){return "<option value=\""+esc(v)+"\" "+(String(v)===String(x.value)?"selected":"")+">"+esc(v)+"</option>"}).join("")+"</select>":registryInput(x);
      return "<div class='topic'><b>"+esc(x.key)+"</b> — "+esc(x.description||"")+"<div class='muted'>"+editor+" · پیش‌فرض: "+esc(x.default)+"</div><button type='button' onclick='updateRegisteredSetting(\\'"+esc(x.key)+"\\')'>ذخیره</button> <button type='button' onclick='resetRegisteredSetting(\\'"+esc(x.key)+"\\')'>بازنشانی</button></div>";
    }).join("")||"Registry خالی است";
  }catch(e){box.textContent="خطا: "+e.message}
}
async function resetRegisteredSetting(key){try{await req("/settings/registry/"+encodeURIComponent(key)+"/reset",{method:"POST"});setText("registryout","تنظیم "+key+" بازنشانی شد.");await loadSettings();await loadRegistry()}catch(e){setText("registryout","خطا: "+e.message)}}

function byId(id) { return document.getElementById(id); }

async function req(url, opt) {
  var r = await fetch(url, opt || {});
  var text = await r.text();
  var j = {};
  try { j = JSON.parse(text); } catch (e) { throw Error("پاسخ نامعتبر از سرور (HTTP " + r.status + ")"); }
  if (!r.ok) throw Error(j.detail || j.message || ("HTTP " + r.status));
  return j;
}

function esc(v) {
  return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
}
function setText(id, value) { var e = byId(id); if (e) e.textContent = value; }

async function loadUsers() {
  var box = byId("users"); if (!box) return; box.textContent = "در حال بارگذاری...";
  try {
    var j = await req("/settings/users"), items = j.items || [];
    box.innerHTML = items.map(function (u) {
      var action = u.role === "admin" ? "" : " <button type=\"button\" onclick=\"toggleUser(" + u.id + "," + (!u.active) + ")\">" + (u.active ? "غیرفعال‌کردن" : "فعال‌کردن") + "</button>";
      return "<div class=\"topic\"><b>" + esc(u.username) + "</b> — " + esc(u.display_name || "بدون نام") + " — نقش: " + esc(u.role) + " — " + (u.active ? "فعال" : "غیرفعال") + action + "</div>";
    }).join("") || "کاربری ثبت نشده است";
  } catch (e) { box.textContent = "خطا در بارگذاری کاربران: " + e.message; }
}
async function toggleUser(id, active) { try { await req("/admin/users/" + id + "/active?active=" + active, {method:"PATCH"}); await loadUsers(); } catch (e) { setText("userout", e.message); } }
async function addUser() {
  try { var j = await req("/admin/users", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:byId("nu").value,password:byId("np").value,display_name:byId("nd").value,active:true})});
    setText("userout", "کاربر ایجاد شد: " + j.user.username); byId("nu").value=""; byId("np").value=""; byId("nd").value=""; await loadUsers(); await loadPermissions();
  } catch(e) { setText("userout",e.message); }
}

async function loadSettings() {
  try {
    var j=await req("/settings/config");
    byId("apiurl").value=j.github.api_url||""; byId("repo").value=j.github.repository||""; byId("ghuser").value=j.github.username||"";
    byId("su_enabled").checked=!!j.features.self_update_enabled; byId("su_approved").checked=!!j.features.self_update_approved; byId("su_health").value=j.features.self_update_health_url||"";
    byId("sr_enabled").checked=!!j.features.self_repair_enabled; byId("sr_approval").checked=!!j.features.self_repair_require_approval;
    byId("lf_enabled").checked=!!j.features.learning_fast_enabled; byId("lf_interval").value=j.features.learning_interval_seconds; byId("lf_retries").value=j.features.learning_max_retries;
    if (byId("log_level")) byId("log_level").value=j.logging && j.logging.level ? j.logging.level : "WARNING";
    byId("cpu_percent").value=j.resources.cpu_percent; byId("cpu_threads").value=j.resources.cpu_threads; byId("ram_percent").value=j.resources.ram_percent; byId("gpu_layers").value=j.resources.gpu_layers;
    setText("gitout",j.github.token_configured?"Token تنظیم شده است":"Token تنظیم نشده است"); await loadResourceStatus();
  } catch(e) { setText("gitout","خطا در بارگذاری تنظیمات: "+e.message); }
}

async function loadResourceStatus() {
  try {
    var j=await req("/scheduler/status?x="+Date.now()), live=j.resources||{};
    var text="تنظیم‌شده: CPU "+live.cpu_limit_percent+"% · "+live.cpu_threads+" thread · RAM "+live.ram_limit_percent+"% · GPU "+live.gpu_layers+" layer";
    if(live.cpu_percent!=null) text += " | مصرف لحظه‌ای: CPU "+live.cpu_percent+"% · RAM "+live.ram_percent+"%";
    setText("resourceout",text);
  } catch(e) { setText("resourceout","خطا در خواندن منابع: "+e.message); }
}

async function saveLogging(){try{var j=await req("/settings/logging",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({level:byId("log_level").value})});setText("logout","تنظیمات لاگ ذخیره و اعمال شد: "+j.logging.level)}catch(e){setText("logout",e.message)}}
async function saveGithubConfig(){try{await req("/settings/github",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({api_url:byId("apiurl").value.trim(),repository:byId("repo").value.trim(),username:byId("ghuser").value.trim()})});setText("gitout","تنظیمات GitHub ذخیره شد")}catch(e){setText("gitout",e.message)}}
async function saveToken(){try{var j=await req("/settings/github-token",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:byId("token").value})});setText("gitout",j.authenticated?"Token معتبر و متصل به @"+j.login:"Token حذف شد");byId("token").value="";await loadSettings()}catch(e){setText("gitout",e.message)}}
async function checkGit(){try{var j=await req("/git/check");setText("gitout",j.message||j.status||"بررسی انجام شد")}catch(e){setText("gitout","خطا در بررسی اتصال: "+e.message)}}
async function saveFeatures(){try{await req("/settings/features",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({self_update_enabled:byId("su_enabled").checked,self_update_approved:byId("su_approved").checked,self_update_health_url:byId("su_health").value,self_repair_enabled:byId("sr_enabled").checked,self_repair_require_approval:byId("sr_approval").checked,learning_fast_enabled:byId("lf_enabled").checked,learning_interval_seconds:Number(byId("lf_interval").value||3600),learning_max_retries:Number(byId("lf_retries").value||5)})});setText("suout","تنظیمات ذخیره شد");setText("srout","تنظیمات ذخیره شد");setText("lfout","تنظیمات ذخیره شد");await loadSettings()}catch(e){setText("suout",e.message);setText("srout",e.message);setText("lfout",e.message)}}

window.saveResources=async function saveResources(){
  setText("resourceout","در حال ذخیره و اعمال منابع...");
  try{var p={cpu_percent:Number(byId("cpu_percent").value||70),cpu_threads:Number(byId("cpu_threads").value||8),ram_percent:Number(byId("ram_percent").value||80),gpu_layers:Number(byId("gpu_layers").value||0)};
    var j=await req("/settings/resources",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
    byId("cpu_percent").value=j.resources.cpu_percent;byId("cpu_threads").value=j.resources.cpu_threads;byId("ram_percent").value=j.resources.ram_percent;byId("gpu_layers").value=j.resources.gpu_layers;
    await loadResourceStatus(); setText("resourceout","ذخیره و اعمال شد: CPU "+j.resources.cpu_percent+"% · "+j.resources.cpu_threads+" thread · RAM "+j.resources.ram_percent+"% · GPU "+j.resources.gpu_layers+" layer");
  }catch(e){setText("resourceout","خطا در ذخیره منابع: "+e.message)}
};

var PERM_TOOLS=["chat","code-generation","code-execution","learning","scheduler","github","security","database","voice","models","memory","web","projects","eval","self-update","self-repair","help","tools"];
function permissionCell(uid,tool,action,allowed){var key=uid+":"+tool+":"+action;return "<label style=\"display:inline-block;margin:3px\"><input type=\"checkbox\" data-permission-key=\""+esc(key)+"\" data-uid=\""+uid+"\" data-tool=\""+esc(tool)+"\" data-action=\""+esc(action)+"\" "+(allowed?"checked":"")+"> "+esc(tool)+":"+esc(action)+"</label>"}
async function loadPermissions(){var box=byId("permissions");if(!box)return;box.textContent="در حال بارگذاری...";try{var pair=await Promise.all([req("/settings/users"),req("/settings/tool-permissions")]);var usersList=pair[0].items||[],items=pair[1].items||[],map={};items.forEach(function(x){map[x.user_id+":"+x.tool_name+":"+x.action]=!!x.allowed});box.innerHTML=usersList.map(function(user){var html="<div class=\"topic\"><b>"+esc(user.username)+"</b> — "+esc(user.role)+"<div>";PERM_TOOLS.forEach(function(tool){["read","write","execute"].forEach(function(action){html+=permissionCell(user.id,tool,action,!!map[user.id+":"+tool+":"+action])})});return html+"</div></div>"}).join("")||"کاربری ثبت نشده است";box.querySelectorAll("[data-permission-key]").forEach(function(input){input.addEventListener("change",function(){setPermission(Number(this.dataset.uid),this.dataset.tool,this.dataset.action,this.checked)})})}catch(e){box.textContent="خطا در بارگذاری مجوزها: "+e.message}}
async function setPermission(uid,tool,action,allowed){try{await req("/settings/tool-permissions",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:uid,tool_name:tool,action:action,allowed:allowed})})}catch(e){alert("خطا در ذخیره مجوز: "+e.message);await loadPermissions()}}
async function loginGit(){try{var j=await req("/git/login",{method:"POST"});setText("gitout",j.message||"درخواست ورود ارسال شد")}catch(e){setText("gitout",e.message)}}
async function logoutGit(){try{var j=await req("/git/logout",{method:"POST"});setText("gitout",j.message||"خروج انجام شد");await loadSettings()}catch(e){setText("gitout",e.message)}}
async function createCourse(){try{var lines=byId("ct").value.split(/\n+/).map(function(x){return x.trim()}).filter(Boolean);var topics=lines.map(function(x){var p=x.split("|").map(function(v){return v.trim()});return{title:p[0],goal:p[1]||"",source_url:p[2]||""}});var j=await req("/settings/courses",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:byId("cn").value,description:byId("cd").value,topics:topics})});setText("courseout","آموزش ساخته شد: "+j.id);await loadCourses()}catch(e){setText("courseout",e.message)}}
async function startCourse(id){try{await req("/settings/courses/"+id+"/start",{method:"POST"});await loadCourses()}catch(e){setText("courseout",e.message)}}


async function loadProviderCatalog(){
  var p=byId("providers"),m=byId("models");if(!p&&!m)return;
  try{
    var j=await req("/settings/providers");
    if(p)p.innerHTML=(j.providers||[]).map(function(x){
      var action=x.enabled?"غیرفعال‌کردن":"فعال‌کردن";
      return "<div class='topic'><b>#"+esc(x.id)+" "+esc(x.name)+"</b> — "+esc(x.protocol)+" — "+(x.enabled?"فعال":"غیرفعال")+
        " <button type='button' onclick='toggleProviderCatalog("+x.id+","+(!x.enabled)+")'>"+action+"</button>"+
        " <button type='button' onclick='healthProviderCatalog("+x.id+")'>بررسی اتصال</button>"+
        " <button type='button' onclick='deleteProviderCatalog("+x.id+")'>حذف</button>"+
        " <span id='provider-health-"+x.id+"' class='muted'></span></div>";
    }).join("")||"Provider ثبت نشده است";
    if(m)m.innerHTML=(j.models||[]).map(function(x){
      return "<div class='topic'><b>Provider #"+esc(x.provider_id)+" / "+esc(x.model_id)+"</b> — priority "+esc(x.priority)+" — "+(x.enabled?"فعال":"غیرفعال")+
        " <button type='button' onclick='toggleModelCatalog("+x.provider_id+",\'"+esc(x.model_id)+"\',"+(!x.enabled)+")'>"+(x.enabled?"غیرفعال‌کردن":"فعال‌کردن")+"</button>"+
        " <button type='button' onclick='healthModelCatalog("+x.provider_id+",\'"+esc(x.model_id)+"\')'>بررسی مدل</button>"+
        " <button type='button' onclick='deleteModelCatalog("+x.provider_id+",\'"+esc(x.model_id)+"\')'>حذف</button>"+
        " <span id='model-health-"+x.provider_id+"-"+esc(x.model_id)+"' class='muted'></span></div>";
    }).join("")||"Model ثبت نشده است";
  }catch(e){if(p)p.textContent="خطا: "+e.message}
}
async function toggleProviderCatalog(id,enabled){
  try{
    var j=await req("/settings/providers"),x=(j.providers||[]).find(function(v){return Number(v.id)===Number(id)});
    if(!x)throw Error("Provider پیدا نشد");
    await req("/settings/providers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:x.name,protocol:x.protocol,endpoint:x.endpoint,auth_type:x.auth_type,secret:"",version:x.version||"",capabilities:x.capabilities||{},timeout_seconds:Number(x.timeout_seconds||30),enabled:enabled})});
    await loadProviderCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function healthProviderCatalog(id){
  var out=byId("provider-health-"+id);if(out)out.textContent="در حال بررسی...";
  try{var j=await req("/settings/providers/"+id+"/health",{method:"POST"});if(out)out.textContent=j.healthy?"سالم · "+j.latency_ms+"ms":"خطا: "+(j.error||"نامشخص")}catch(e){if(out)out.textContent="خطا: "+e.message}
}
async function toggleModelCatalog(providerId,modelId,enabled){
  try{
    var j=await req("/settings/providers"), models=j.models||[], x=models.find(function(v){return Number(v.provider_id)===Number(providerId)&&v.model_id===modelId});
    if(!x)throw Error("Model پیدا نشد");
    await req("/settings/models",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({provider_id:Number(x.provider_id),model_id:x.model_id,tasks:x.tasks||[],context_length:x.context_length||null,limits:x.limits||{},priority:Number(x.priority||100),version:x.version||"",enabled:enabled})});
    await loadProviderCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function healthModelCatalog(providerId,modelId){
  var out=byId("model-health-"+providerId+"-"+modelId);if(out)out.textContent="در حال بررسی...";
  try{var j=await req("/settings/models/"+providerId+"/"+encodeURIComponent(modelId)+"/health",{method:"POST"});if(out)out.textContent=j.available?"سالم · "+(j.latency_ms||0)+"ms":"در دسترس نیست: "+(j.error||"نامشخص")}catch(e){if(out)out.textContent="خطا: "+e.message}
}
async function deleteModelCatalog(providerId,modelId){
  if(!confirm("این مدل از کاتالوگ حذف شود؟"))return;
  try{await req("/settings/models/"+providerId+"/"+encodeURIComponent(modelId),{method:"DELETE"});await loadProviderCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}
}

async function loadLearningSourcesCatalog(){
  var box=byId("learning-sources-catalog");if(!box)return;
  try{var j=await req("/settings/learning-sources");box.innerHTML=(j.items||[]).map(function(x){
    return "<div class='topic'><b>"+esc(x.title||x.url)+"</b> · "+esc(x.source_type)+" · v"+esc(x.version)+" · "+esc(x.status)+
      " <button type='button' onclick='reviewLearningSource("+x.id+",\'approved\')'>تأیید</button>"+
      " <button type='button' onclick='reviewLearningSource("+x.id+",\'rejected\')'>رد</button></div>";
  }).join("")||"منبع ثبت نشده است"}catch(e){box.textContent="خطا: "+e.message}
}
async function addLearningSourceCatalog(){
  try{await req("/settings/learning-sources",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    url:byId("ls_url").value.trim(),source_type:byId("ls_type").value.trim()||"custom",product:byId("ls_product").value.trim(),
    version:byId("ls_version").value.trim(),priority:Number(byId("ls_priority").value||100),provenance:{ui:true}
  })});await loadLearningSourcesCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}
}
async function reviewLearningSource(id,status){try{await req("/settings/learning-sources/"+id+"/"+status,{method:"POST"});await loadLearningSourcesCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}}

async function loadControlPlane(){
  var ns=byId("cp_namespace"),box=byId("controlplane");if(!box)return;
  try{
    var n=await req("/settings/control-plane/namespaces");
    if(ns&&ns.options.length===1)(n.namespaces||[]).forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;ns.appendChild(o)});
    var q=ns&&ns.value?"?namespace="+encodeURIComponent(ns.value):"";
    var j=await req("/settings/control-plane"+q);
    box.innerHTML=(j.items||[]).map(function(x){
      return "<div class='topic'><b>"+esc(x.namespace)+"/"+esc(x.name)+"</b> v"+esc(x.version)+" — "+(x.enabled?"فعال":"غیرفعال")+
        "<pre>"+esc(JSON.stringify(x.payload,null,2))+"</pre>"+
        "<button type='button' onclick='editControlPlane("+JSON.stringify(x)+")'>ویرایش</button>"+
        "<button type='button' onclick='toggleControlPlane("+JSON.stringify(x.namespace)+","+JSON.stringify(x.name)+","+(!x.enabled)+")'>"+(x.enabled?"غیرفعال":"فعال")+"</button>"+
        "<button type='button' onclick='deleteControlPlane("+JSON.stringify(x.namespace)+","+JSON.stringify(x.name)+")'>حذف</button></div>";
    }).join("")||"رکوردی ثبت نشده است";
    var a=await req("/settings/control-plane/actions?limit=20");
    var ab=byId("controlactions");if(ab)ab.innerHTML=(a.items||[]).map(function(x){return "<div class='topic'>"+esc(x.action)+" · "+esc(x.namespace)+" · "+esc(x.status)+" · "+esc(x.progress)+"%</div>"}).join("")||"عملیاتی ثبت نشده است";
  }catch(e){box.textContent="خطا: "+e.message}
}
async function saveControlPlane(){
  try{
    var ns=byId("cp_namespace").value,name=byId("cp_name").value.trim(),payload=JSON.parse(byId("cp_payload").value||"{}"),enabled=byId("cp_enabled").checked;
    if(!ns||!name)throw Error("دسته و نام الزامی است");
    await req("/settings/control-plane/"+encodeURIComponent(ns),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name,payload:payload,enabled:enabled})});
    await loadControlPlane();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
function editControlPlane(x){byId("cp_namespace").value=x.namespace;byId("cp_name").value=x.name;byId("cp_payload").value=JSON.stringify(x.payload||{},null,2);byId("cp_enabled").checked=!!x.enabled}
async function toggleControlPlane(ns,name,enabled){await req("/settings/control-plane/"+encodeURIComponent(ns)+"/"+encodeURIComponent(name)+"/"+(enabled?"enable":"disable"),{method:"POST"});await loadControlPlane()}
async function deleteControlPlane(ns,name){if(!confirm("این رکورد حذف شود؟"))return;await req("/settings/control-plane/"+encodeURIComponent(ns)+"/"+encodeURIComponent(name),{method:"DELETE"});await loadControlPlane()}

async function loadUIActions(){
  var box=byId("ui-actions");if(!box)return;
  try{
    var j=await req("/settings/ui-actions");
    box.innerHTML=(j.items||[]).map(function(a){
      return "<div class='topic'><b>"+esc(a.label)+"</b><div class='muted'>"+esc(a.description)+"</div><button type='button' data-action-id='"+esc(a.id)+"' data-method='"+esc(a.method)+"' data-endpoint='"+esc(a.endpoint)+"'>اجرا</button><span id='action-"+esc(a.id)+"' class='muted' style='margin-right:8px'></span></div>";
    }).join("")||"عملیات گرافیکی ثبت نشده است";
    box.querySelectorAll("[data-action-id]").forEach(function(button){
      button.addEventListener("click",function(){runUIAction(this.dataset.actionId,this.dataset.method,this.dataset.endpoint)});
    });
  }catch(e){box.textContent="خطا در بارگذاری عملیات گرافیکی: "+e.message}
}
async function runUIAction(id,method,endpoint){
  var out=byId("action-"+id);if(out)out.textContent="در حال اجرا...";
  try{var j=await req(endpoint,{method:method});if(out)out.textContent="انجام شد: "+JSON.stringify(j).slice(0,300)}
  catch(e){if(out)out.textContent="خطا: "+e.message}
}
async function pauseCourse(id){try{await req("/settings/courses/"+id+"/pause",{method:"POST"});setText("courseout","آموزش متوقف شد.");await loadCourses()}catch(e){setText("courseout",e.message)}}

async function loadCourses(){var box=byId("courses");if(!box)return;try{var j=await req("/settings/courses");box.innerHTML=(j.items||[]).map(function(c){return "<div class=\"card\"><h3>"+esc(c.name)+"</h3><p>"+esc(c.description)+"</p><div class=\"bar\"><div class=\"fill\" style=\"width:"+c.progress_percent+"%\">"+c.progress_percent+"%</div></div><p class=\"muted\">"+c.completed_topics+" از "+c.total_topics+" سرفصل کامل شده"+(c.current?" · اکنون: "+esc(c.current.title)+" · مرحله: "+esc(c.current.phase):"")+"</p><button type=\"button\" onclick=\"startCourse("+c.id+")\">شروع / ادامه یادگیری</button> <button type=\"button\" onclick=\"pauseCourse("+c.id+")\">توقف</button></div>"}).join("")||"آموزشی نیست"}catch(e){box.textContent="خطا در بارگذاری آموزش‌ها: "+e.message}}

loadSettings();loadRegistry();loadUsers();loadPermissions();loadCourses();loadUIActions();loadProviderCatalog();setInterval(loadCourses,10000);setInterval(loadResourceStatus,5000);

loadLearningSourcesCatalog();
