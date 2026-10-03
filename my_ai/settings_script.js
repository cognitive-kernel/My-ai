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
function filterRegistry(query){ var q=String(query||"").toLowerCase(); var box=byId("settings-registry"); if(!box)return; Array.from(box.children).forEach(function(row){ row.style.display=(!q || row.textContent.toLowerCase().indexOf(q)>=0)?"":"none"; }); }
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
async function createCourse(){try{var lines=byId("ct").value.split(/\n+/).map(function(x){return x.trim()}).filter(Boolean);var topics=lines.map(function(x){var p=x.split("|").map(function(v){return v.trim()});return{title:p[0],goal:p[1]||"",source_url:p[2]||""}});var j=await req("/settings/courses",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({provider_id:(byId("pc_provider_id").value?Number(byId("pc_provider_id").value):null),name:byId("cn").value,description:byId("cd").value,topics:topics,llm_model:byId("course_llm").value.trim(),schedule:byId("course_schedule").value.trim()||"weekly",mastery_threshold:Number(byId("course_mastery").value||0.8),source_policy:byId("course_source_policy").value,mode:byId("course_mode").value})});setText("courseout","آموزش ساخته شد: "+j.id);await loadCourses()}catch(e){setText("courseout",e.message)}}
async function startCourse(id){try{await req("/settings/courses/"+id+"/start",{method:"POST"});await loadCourses()}catch(e){setText("courseout",e.message)}}


async function saveProviderCatalog(){
  try{
    var capabilities={};try{capabilities=byId("pc_capabilities").value.trim()?JSON.parse(byId("pc_capabilities").value):{};if(!capabilities||typeof capabilities!=="object"||Array.isArray(capabilities))throw Error("Capabilities باید JSON object باشد");}catch(e){setText("catalogout","Capabilities نامعتبر: "+e.message);return;}var body={provider_id:(byId("pc_provider_id").value?Number(byId("pc_provider_id").value):null),name:byId("pc_name").value.trim(),protocol:byId("pc_protocol").value.trim(),endpoint:byId("pc_endpoint").value.trim(),auth_type:byId("pc_auth").value.trim()||"none",secret:byId("pc_secret").value,version:byId("pc_version").value.trim(),capabilities:capabilities,timeout_seconds:Number(byId("pc_timeout").value||30),enabled:byId("pc_enabled").checked};
    await req("/settings/providers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    byId("pc_provider_id").value="";byId("pc_secret").value="";setText("catalogout","Provider ذخیره شد.");await loadProviderCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function saveModelCatalog(){
  try{
    var tasks=byId("mc_tasks").value.split(",").map(function(x){return x.trim()}).filter(Boolean);
    var limits={};try{limits=byId("mc_limits").value.trim()?JSON.parse(byId("mc_limits").value):{};if(!limits||typeof limits!=="object"||Array.isArray(limits))throw Error("Limits باید JSON object باشد");}catch(e){setText("catalogout","Limits نامعتبر: "+e.message);return;}await req("/settings/models",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({provider_id:Number(byId("mc_provider").value),model_id:byId("mc_model").value.trim(),tasks:tasks,context_length:(byId("mc_context").value?Number(byId("mc_context").value):null),limits:limits,priority:Number(byId("mc_priority").value||100),version:byId("mc_version").value.trim(),enabled:byId("mc_enabled").checked})});
    setText("catalogout","Model ذخیره شد.");await loadProviderCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function loadProviderCatalog(){
  var p=byId("providers"),m=byId("models");if(!p&&!m)return;
  try{
    var j=await req("/settings/providers");
    if(p)p.innerHTML=(j.providers||[]).map(function(x){
      var action=x.enabled?"غیرفعال‌کردن":"فعال‌کردن";
      return "<div class='topic'><b>#"+esc(x.id)+" "+esc(x.name)+"</b> — "+esc(x.protocol)+" — "+(x.enabled?"فعال":"غیرفعال")+
        " <button type='button' onclick='toggleProviderCatalog("+x.id+","+(!x.enabled)+")'>"+action+"</button>"+
        " <button type='button' onclick='editProviderCatalog("+x.id+")'>ویرایش</button>"+
        " <button type='button' onclick='addProviderKeyGUI("+x.id+")'>افزودن کلید</button>"+
        " <button type='button' onclick='rotateProviderKeyGUI("+x.id+")'>چرخش کلید</button>"+
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
async function editProviderCatalog(id){
  try{var j=await req("/settings/providers"),x=(j.providers||[]).find(function(v){return Number(v.id)===Number(id)});if(!x)throw Error("Provider پیدا نشد");
    byId("pc_provider_id").value=x.id;byId("pc_name").value=x.name||"";byId("pc_protocol").value=x.protocol||"";byId("pc_endpoint").value=x.endpoint||"";byId("pc_auth").value=x.auth_type||"none";byId("pc_version").value=x.version||"";byId("pc_timeout").value=x.timeout_seconds||30;byId("pc_capabilities").value=JSON.stringify(x.capabilities||{});byId("pc_enabled").checked=!!x.enabled;byId("pc_secret").value="";setText("catalogout","Provider #"+x.id+" برای ویرایش بارگذاری شد.");
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function addProviderKeyGUI(id){
  var name=prompt("نام کلید:");if(!name)return;var secret=prompt("مقدار کلید:");if(!secret)return;
  try{await req("/settings/providers/"+id+"/keys",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key_name:name,secret:secret,priority:100})});setText("catalogout","کلید ثبت شد.");}catch(e){setText("catalogout","خطا: "+e.message)}
}
async function rotateProviderKeyGUI(id){
  if(!confirm("کلید فعال این Provider جابه‌جا شود؟"))return;
  try{var j=await req("/settings/providers/"+id+"/keys/rotate",{method:"POST"});setText("catalogout","کلید فعال: "+(j.active_key||"نامشخص"));}catch(e){setText("catalogout","خطا: "+e.message)}
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

async function loadMigrationGUI(){
  try{
    var j=await req("/settings/database/migration");
    setText("migrationout",JSON.stringify(j,null,2));
  }catch(e){setText("migrationout","خطا: "+e.message)}
}
async function runMigrationGUI(){
  if(!confirm("Migration پیکربندی اجرا شود؟"))return;
  try{
    var j=await req("/settings/database/migration",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
    setText("migrationout","Migration اجرا شد: schema version "+j.version);
    await loadMigrationGUI();
  }catch(e){setText("migrationout","خطا: "+e.message)}
}

async function backupDatabaseGUI(){
  try{var path=byId("backup_path").value.trim();var j=await req("/settings/database/backup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:path,overwrite:false})});setText("backupout","Backup انجام شد: "+j.path)}catch(e){setText("backupout","خطا: "+e.message)}
}
async function restoreDatabaseGUI(){
  if(!confirm("بازیابی DB انجام شود؟"))return;
  try{var path=byId("backup_path").value.trim();var j=await req("/settings/database/restore",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:path,confirm:true})});setText("backupout","Restore انجام شد: "+j.path)}catch(e){setText("backupout","خطا: "+e.message)}
}

async function loadRoutingGUI(){
  var box=byId("routingitems"); if(!box)return;
  try{
    var j=await req("/settings/routing");
    var rules=(j.rules||[]).map(function(x){return "<div><b>Rule:</b> "+esc(x.task)+" → "+esc(x.model_id)+" · priority "+esc(x.priority)+" · "+(x.enabled?"فعال":"غیرفعال")+"</div>"}).join("");
    var fb=Object.keys(j.fallbacks||{}).map(function(task){var ids=(j.fallbacks[task]||[]).map(function(x){return x.model_id}).join(" → ");return "<div><b>Fallback "+esc(task)+":</b> "+esc(ids||"تعریف نشده")+"</div>"}).join("");
    box.innerHTML=rules+fb||"Routing/Fallback ثبت نشده است";
  }catch(e){box.textContent="خطا: "+e.message}
}
async function deleteProviderCatalog(id){if(!confirm("این Provider حذف شود؟"))return;try{await req("/settings/providers/"+encodeURIComponent(id)+"?confirm=true",{method:"DELETE"});await loadProviderCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}}
async function saveRoutingRuleGUI(){
  try{await req("/settings/routing/rule",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({task:byId("route_task").value.trim(),model_id:byId("route_model").value.trim(),provider_id:byId("route_provider").value?Number(byId("route_provider").value):null,priority:Number(byId("route_priority").value||100),enabled:true})});setText("routingout","Routing Rule ذخیره شد.");await loadRoutingGUI()}catch(e){setText("routingout","خطا: "+e.message)}
}
async function saveFallbackGUI(){
  try{await req("/settings/routing/fallback",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:"ui",task:byId("fallback_task").value.trim()||"general",model_ids:byId("fallback_models").value.split(",").map(function(x){return x.trim()}).filter(Boolean),enabled:true})});setText("routingout","Fallback Chain ذخیره شد.");await loadRoutingGUI()}catch(e){setText("routingout","خطا: "+e.message)}
}

async function loadLearningSourcesCatalog(){
  var box=byId("learning-sources-catalog");if(!box)return;
  try{var j=await req("/settings/learning-sources");box.innerHTML=(j.items||[]).map(function(x){
    return "<div class='topic'><b>"+esc(x.title||x.url)+"</b> · "+esc(x.source_type)+" · v"+esc(x.version)+" · "+esc(x.status)+
      " <button type='button' onclick='editLearningSource("+x.id+")'>ویرایش</button>"+ " <button type='button' onclick='reviewLearningSource("+x.id+",\'approved\')'>تأیید</button>"+
      " <button type='button' onclick='reviewLearningSource("+x.id+",\'rejected\')'>رد</button>"+
      " <button type='button' onclick='deleteLearningSource("+x.id+")'>حذف</button></div>";
  }).join("")||"منبع ثبت نشده است"}catch(e){box.textContent="خطا: "+e.message}
}
async function addLearningSourceCatalog(){
  try{await req("/settings/learning-sources",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
    url:byId("ls_url").value.trim(),source_type:byId("ls_type").value.trim()||"custom",product:byId("ls_product").value.trim(),
    version:byId("ls_version").value.trim(),priority:Number(byId("ls_priority").value||100),weight:Number(byId("ls_weight").value||1),provenance:{ui:true}
  })});await loadLearningSourcesCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}
}
async function uploadLearningSourceCatalog(){
  try{
    var file=byId("ls_file").files[0];
    if(!file){setText("catalogout","یک فایل انتخاب کنید.");return;}
    var form=new FormData();
    form.append("file",file);
    form.append("source_type",byId("ls_type").value.trim()||"file");
    form.append("priority",String(Number(byId("ls_priority").value||100)));
    form.append("weight",String(Number(byId("ls_weight").value||1)));
    var j=await req("/settings/learning-sources/upload",{method:"POST",body:form});
    setText("catalogout","منبع آپلود شد: "+j.id);
    byId("ls_file").value="";
    await loadLearningSourcesCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function editLearningSource(id){
  try{
    var j=await req("/settings/learning-sources"),x=(j.items||[]).find(function(v){return Number(v.id)===Number(id)});
    if(!x)throw Error("منبع پیدا نشد");
    var url=prompt("URL / مسیر منبع:",x.url||""); if(url===null)return;
    var title=prompt("عنوان:",x.title||""); if(title===null)return;
    await req("/settings/learning-sources/"+id,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:url,source_type:x.source_type,title:title,priority:Number(x.priority||100),weight:Number(x.weight||1),product:x.product||"",version:x.version||"",compatibility:x.compatibility||""})});
    await loadLearningSourcesCatalog();
  }catch(e){setText("catalogout","خطا: "+e.message)}
}
async function deleteLearningSource(id){if(!confirm("این منبع حذف شود؟"))return;try{await req("/settings/learning-sources/"+id,{method:"DELETE"});await loadLearningSourcesCatalog()}catch(e){setText("catalogout","خطا: "+e.message)}}
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

async function adminGUI(kind){try{var endpoint=kind==="status"?"/settings/providers":kind==="health"?"/settings/metrics":"/settings/control-plane?namespace="+encodeURIComponent(kind==="sessions"?"agent.session":kind==="memory"?"memory.policy":kind==="tools"?"tools.catalog":kind==="policies"?"policies.registry":kind==="learning"?"knowledge.registry":kind==="repairs"?"self_repair.policy":kind==="rollback"?"self_update.policy":"");var x=await req(endpoint);setText("adminguiout",JSON.stringify(x,null,2));}catch(e){setText("adminguiout","خطا: "+e.message)}}
async function loadControlNamespacesGUI(){
  try{
    var j=await req("/settings/control-plane/namespaces"), box=byId("cp_namespace");
    box.innerHTML=(j.items||[]).map(function(x){return "<option value=\""+esc(x)+"\">"+esc(x)+"</option>"}).join("");
    await loadControlRecordsGUI();
  }catch(e){setText("cp_out","خطا: "+e.message)}
}
async function loadControlRecordsGUI(){
  try{
    var ns=byId("cp_namespace").value,j=await req("/settings/control-plane?namespace="+encodeURIComponent(ns));
    byId("cp_records").innerHTML=(j.items||[]).map(function(x){return "<div><b>"+esc(x.name)+"</b> v"+x.version+" — "+(x.enabled?"فعال":"غیرفعال")+" <button onclick=\"editControlRecordGUI('"+esc(x.name)+"')\">ویرایش</button></div>"}).join("")||"رکوردی ثبت نشده است";
  }catch(e){setText("cp_out","خطا: "+e.message)}
}
async function editControlRecordGUI(name){
  try{var ns=byId("cp_namespace").value,x=await req("/settings/control-plane/"+encodeURIComponent(ns)+"/"+encodeURIComponent(name));byId("cp_name").value=x.name;byId("cp_payload").value=JSON.stringify(x.payload,null,2);byId("cp_enabled").checked=!!x.enabled}
  catch(e){setText("cp_out","خطا: "+e.message)}
}
async function toggleControlRecordGUI(name,enabled){try{var ns=byId("cp_namespace").value;await req("/settings/control-plane/"+encodeURIComponent(ns)+"/"+encodeURIComponent(name)+"/"+(enabled?"enable":"disable"),{method:"POST"});await loadControlRecordsGUI();setText("cp_out",enabled?"رکورد فعال شد.":"رکورد غیرفعال شد.")}catch(e){setText("cp_out","خطا: "+e.message)}}
async function deleteControlRecordGUI(name){if(!confirm("این رکورد حذف شود؟"))return;try{var ns=byId("cp_namespace").value;await req("/settings/control-plane/"+encodeURIComponent(ns)+"/"+encodeURIComponent(name),{method:"DELETE"});await loadControlRecordsGUI();setText("cp_out","رکورد حذف شد.")}catch(e){setText("cp_out","خطا: "+e.message)}}
async function startControlActionGUI(){try{var ns=byId("cp_namespace").value,action=byId("cp_action").value.trim(),target=byId("cp_target").value.trim();if(!action)throw Error("نام عملیات الزامی است");var j=await req("/settings/control-plane/actions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:action,namespace:ns,target_id:target||null})});byId("cp_action_id").value=j.id;setText("cp_action_out","عملیات شروع شد: "+j.id);await loadControlActionGUI(j.id)}catch(e){setText("cp_action_out","خطا: "+e.message)}}
async function loadControlActionGUI(id){if(!id)return;try{var j=await req("/settings/control-plane/actions/"+encodeURIComponent(id));setText("cp_action_out","status="+j.status+" · progress="+j.progress+"%"+(j.error?" · "+j.error:""))}catch(e){setText("cp_action_out","خطا: "+e.message)}}
async function updateControlActionGUI(){try{var id=byId("cp_action_id").value.trim();if(!id)throw Error("شناسه عملیات الزامی است");var result=JSON.parse(byId("cp_action_result").value||"{}");var j=await req("/settings/control-plane/actions/"+encodeURIComponent(id),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:byId("cp_action_status").value,progress:Number(byId("cp_action_progress").value||0),result:result,error:byId("cp_action_error").value||""})});setText("cp_action_out","عملیات به‌روزرسانی شد: "+j.status+" · "+j.progress+"%")}catch(e){setText("cp_action_out","خطا: "+e.message)}}
async function saveControlRecordGUI(){
  try{var ns=byId("cp_namespace").value,name=byId("cp_name").value.trim(),payload=JSON.parse(byId("cp_payload").value||"{}");var x=await req("/settings/control-plane/"+encodeURIComponent(ns),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name,payload:payload,enabled:byId("cp_enabled").checked})});setText("cp_out","ذخیره شد: "+x.name+" v"+x.version);await loadControlRecordsGUI()}
  catch(e){setText("cp_out","خطا: "+e.message)}
}
async function savePromptGUI(){try{await req("/settings/prompts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:byId("prompt_name").value.trim(),text:byId("prompt_text").value,task:byId("prompt_task").value.trim()||"default",version:"1",enabled:false})});setText("registry_agent_out","Prompt منتشر شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function testPromptGUI(){try{var name=byId("prompt_name").value.trim(),input=byId("prompt_test_input").value.trim();if(!name||!input)throw Error("نام Prompt و ورودی آزمایشی الزامی است");var j=await req("/settings/prompts/"+encodeURIComponent(name)+"/test",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({input:input})});setText("registry_agent_out","نتیجه تست:\n"+j.output)}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function activatePromptGUI(){try{await req("/settings/prompts/"+encodeURIComponent(byId("prompt_name").value.trim())+"/activate",{method:"POST"});setText("registry_agent_out","Prompt فعال شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function savePolicyGUI(){try{await req("/settings/policies",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:byId("policy_name").value.trim(),policy:JSON.parse(byId("policy_payload").value||"{}"),version:"1",enabled:false})});setText("registry_agent_out","Policy منتشر شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function proposePluginGUI(){try{await req("/settings/plugins",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:byId("plugin_name").value.trim(),source:byId("plugin_source").value.trim(),version:byId("plugin_version").value.trim(),capabilities:byId("plugin_caps").value.split(",").map(function(x){return x.trim()}).filter(Boolean),checksum:""})});setText("registry_agent_out","Plugin پیشنهاد شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function approvePluginGUI(){try{await req("/settings/plugins/"+encodeURIComponent(byId("plugin_name").value.trim())+"/approve",{method:"POST"});setText("registry_agent_out","Plugin تأیید شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function rejectPluginGUI(){try{await req("/settings/plugins/"+encodeURIComponent(byId("plugin_name").value.trim())+"/reject",{method:"POST"});setText("registry_agent_out","Plugin رد شد.")}catch(e){setText("registry_agent_out","خطا: "+e.message)}}
async function loadProfilesGUI(){
  try{
    var j=await req("/settings/profiles"),box=byId("profiles");
    if(!box)return;
    box.innerHTML=(j.items||[]).filter(function(x){return x.name!=="__active__"}).map(function(x){
      var active=j.active===x.name;
      return "<div class='topic'><b>"+esc(x.name)+"</b> v"+esc(x.version)+" — "+(active?"فعال":"ذخیره‌شده")+
        " <button type='button' onclick='editProfileGUI("+JSON.stringify(x.name)+")'>ویرایش</button></div>";
    }).join("")||"پروفایلی ثبت نشده است";
  }catch(e){setText("profileout","خطا: "+e.message)}
}
async function editProfileGUI(name){
  try{
    var j=await req("/settings/profiles/"+encodeURIComponent(name));
    byId("profile_name").value=j.name;
    byId("profile_settings").value=JSON.stringify(j.settings||{},null,2);
    byId("profile_activate").checked=!!j.active;
  }catch(e){setText("profileout","خطا: "+e.message)}
}
async function saveProfileGUI(){
  try{
    var name=byId("profile_name").value.trim(),settings=JSON.parse(byId("profile_settings").value||"{}");
    if(!name)throw Error("نام پروفایل الزامی است");
    var j=await req("/settings/profiles",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name,settings:settings,activate:byId("profile_activate").checked})});
    setText("profileout","پروفایل ذخیره شد: "+j.name);await loadProfilesGUI();
  }catch(e){setText("profileout","خطا: "+e.message)}
}

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

loadLearningSourcesCatalog();loadRoutingGUI();loadControlNamespacesGUI();loadProfilesGUI();


function moduleGuiEsc(v){return esc(v)}
function moduleGuiKey(v){return encodeURIComponent(String(v)).replace(/%/g,"_")}
function moduleGuiId(prefix,namespace){return prefix+moduleGuiKey(namespace)}
async function loadModuleGui(){
  var box=byId("module-gui-list"); if(!box)return;
  try{
    var j=await req("/settings/control-plane/namespaces");
    var items=j.items||j.namespaces||[];
    if(!items.length){box.textContent="ماژول قابل تنظیمی ثبت نشده است";return;}
    box.innerHTML=items.map(function(ns){
      var name=typeof ns==="string"?ns:(ns.name||ns.namespace||"");
      var key=moduleGuiKey(name);
      return "<details class='moduleCard'>"+
        "<summary>"+moduleGuiEsc(name)+"</summary>"+
        "<div class='moduleFields'>"+
        "<label>نام رکورد<input id='mg-name-"+key+"' placeholder='مثلاً default'></label>"+
        "<label>تنظیمات ماژول<textarea id='mg-payload-"+key+"' rows='7' placeholder='{&quot;enabled&quot;:true}'></textarea></label>"+
        "<label><input id='mg-enabled-"+key+"' type='checkbox' checked> فعال</label>"+
        "</div>"+
        "<div class='moduleActions'><button type='button' onclick='saveModuleGui("+JSON.stringify(name)+")'>ذخیره</button>"+
        "<button type='button' onclick='loadModuleRecordsGui("+JSON.stringify(name)+")'>نمایش رکوردها</button></div>"+
        "<div class='moduleActions'><button type='button' onclick='moduleActionGUI("+JSON.stringify(name)+",\"start\")'>Start</button>"+
        "<button type='button' onclick='moduleActionGUI("+JSON.stringify(name)+",\"pause\")'>Pause</button>"+
        "<button type='button' onclick='moduleActionGUI("+JSON.stringify(name)+",\"resume\")'>Resume</button>"+
        "<button type='button' onclick='moduleActionGUI("+JSON.stringify(name)+",\"stop\")'>Stop</button>"+
        "<button type='button' onclick='moduleActionGUI("+JSON.stringify(name)+",\"retry\")'>Retry</button></div>"+
        "<div id='mg-action-"+key+"' class='muted'>آخرین عملیات: —</div>"+
        "<div id='mg-records-"+key+"' class='muted moduleRecords'></div></details>";
    }).join("");
  }catch(e){box.textContent="خطا در بارگذاری ماژول‌ها: "+e.message}
}
async function moduleActionGUI(namespace,action){
  var key=moduleGuiKey(namespace), out=byId("mg-action-"+key);
  if(out)out.textContent="در حال اجرای "+action+"...";
  try{
    var j=await req("/settings/control-plane/actions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:action,namespace:namespace,target_id:null})});
    if(out)out.textContent="آخرین عملیات: "+action+" · id="+j.id+" · "+(j.status||"started");
    if(j.id)await pollModuleActionGUI(namespace,j.id);
  }catch(e){if(out)out.textContent="خطا: "+e.message}
}
async function pollModuleActionGUI(namespace,id){
  var key=moduleGuiKey(namespace), out=byId("mg-action-"+key), attempts=0;
  while(attempts++<10){
    try{
      var j=await req("/settings/control-plane/actions/"+encodeURIComponent(id));
      if(out)out.textContent="آخرین عملیات: "+j.action+" · "+j.status+" · "+j.progress+"%"+(j.error?" · "+j.error:"");
      if(["completed","failed","cancelled"].indexOf(String(j.status))>=0)return;
      await new Promise(function(resolve){setTimeout(resolve,1000)});
    }catch(e){if(out)out.textContent="خطا در وضعیت عملیات: "+e.message;return}
  }
}

async function saveModuleGui(namespace){
  try{
    var key=moduleGuiKey(namespace), name=byId("mg-name-"+key).value.trim(), raw=byId("mg-payload-"+key).value.trim();
    if(!name)throw Error("نام رکورد الزامی است");
    var payload=raw?JSON.parse(raw):{};
    if(!payload || typeof payload!=="object" || Array.isArray(payload))throw Error("تنظیمات باید JSON object باشد");
    await req("/settings/control-plane/"+encodeURIComponent(namespace),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name,payload:payload,enabled:byId("mg-enabled-"+key).checked})});
    setText("module-gui-out","ماژول "+namespace+" / "+name+" ذخیره شد."); await loadModuleRecordsGui(namespace);
  }catch(e){setText("module-gui-out","خطا: "+e.message)}
}
async function loadModuleRecordsGui(namespace){
  try{
    var j=await req("/settings/control-plane?namespace="+encodeURIComponent(namespace)+"&include_disabled=true");
    var box=byId("mg-records-"+moduleGuiKey(namespace)); if(!box)return;
    box.innerHTML=(j.items||j.records||[]).map(function(x){
      return "<div class='topic'><b>"+moduleGuiEsc(x.name||"رکورد")+"</b> · v"+moduleGuiEsc(x.version||"")+
        " · "+(x.enabled?"فعال":"غیرفعال")+
        "<details><summary>جزئیات</summary><pre style='white-space:pre-wrap'>"+moduleGuiEsc(JSON.stringify(x.payload||{},null,2))+"</pre></details></div>";
    }).join("")||"رکوردی ثبت نشده است";
  }catch(e){setText("module-gui-out","خطا: "+e.message)}
}
loadModuleGui();
