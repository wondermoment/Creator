'use strict';
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search);
let me,config,ticket=0,busy=false,recoveryJob='',recoveryRequired=false,loading=true,readyProject='',activeArticle=null,targetBinding=null;
let accessBlocked=false,sessionEpoch=0;
let sessionPending=false,sessionCheck=null;
let currentTemplate=null,importedSnapshot=false;
const digestPreview=document.createElement('p');digestPreview.id='digest-preview';$('preview').after(digestPreview);
const targetPreview=document.createElement('p');targetPreview.id='target-preview';digestPreview.after(targetPreview);
function showDigest(result,revision){if(result.revision!==revision)throw Error('文章版本已变化，请重新打开');digestPreview.textContent=(result.imported_snapshot?'公众号已保存摘要：':'下次同步摘要：')+(result.next_digest||'暂无正文摘要')+'（已同步的草稿不会自动修改）';}
const recoveryButton=document.createElement('button');recoveryButton.textContent='核对微信回执（不重发）';recoveryButton.hidden=true;$('sync').after(recoveryButton);
const templateInfo=document.createElement('p');targetPreview.after(templateInfo);
const importButton=document.createElement('button');importButton.textContent='读取微信排版并设为后续默认模板';recoveryButton.after(importButton);
function clearAccess(){
 accessBlocked=true;++sessionEpoch;++ticket;me=null;config=null;readyProject='';activeArticle=null;targetBinding=null;recoveryJob='';recoveryRequired=false;loading=false;
 $('binding').hidden=true;$('draft').hidden=true;$('confirm').checked=false;
 for(const id of ['secret','appid','name','project'])$(id).value='';
 $('project').textContent='';
 for(const id of ['article','receipt','secret-status','connection','ip'])$(id).textContent='';
 $('preview').removeAttribute('href');digestPreview.textContent='';targetPreview.textContent='';
 currentTemplate=null;importedSnapshot=false;templateInfo.textContent='';importButton.hidden=true;
 recoveryButton.hidden=true;recoveryButton.style.display='none';updateControls();
 $('status').textContent='登录或访问权限已变化，已清空本页信息。请回工作台登录后重新打开；不会自动重发。';
}
async function api(path,method='GET',body){
 if(accessBlocked)throw Error('请登录后重新打开此页面');
 const epoch=sessionEpoch;
 const r=await fetch(path,{method,cache:'no-store',headers:{'Content-Type':'application/json','x-csrf-token':me?.csrf||''},body:body===undefined?undefined:JSON.stringify(body)});
 if(epoch!==sessionEpoch||accessBlocked)throw Error('旧会话响应已忽略');
 if(r.status===401||r.status===403){clearAccess();throw Error('登录或访问权限已变化，请重新打开页面');}
 const d=await r.json();
 if(epoch!==sessionEpoch||accessBlocked)throw Error('旧会话响应已忽略');
 if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'请求失败，请检查输入');return d;
}
const path=()=>'/api/projects/'+encodeURIComponent($('project').value);
const unresolvedStatuses=['preparing','sending','created','needs_review'];
function selectReceipt(records,binding){
 if(!binding?.appid)return null;
 const current=records.filter(r=>r.appid===binding.appid);
 return current.find(r=>unresolvedStatuses.includes(r.status))||current[0]||null;
}
function show(c){config=c;$('appid').value=c.appid;$('name').value=c.name;$('secret').value='';$('secret-status').textContent=c.has_secret?'密钥已加密保存，不回显':'尚未保存密钥';$('connection').textContent=c.status==='verified_read'?'连接正常，草稿读取已验证。每篇文章的写入结果以同步回执为准。':c.error||'尚未完成连接测试';$('ip').textContent=c.required_ip?'微信要求加入白名单的出口 IP：'+c.required_ip:'';}
async function load(){
 if(accessBlocked)return;
 const n=++ticket,p=$('project').value,base='/api/projects/'+encodeURIComponent(p);
 const current=()=>n===ticket&&p===$('project').value;
 loading=true;readyProject='';config=null;activeArticle=null;recoveryJob='';targetBinding=null;targetPreview.textContent='';
 currentTemplate=null;importedSnapshot=false;templateInfo.textContent='';
 $('binding').hidden=true;$('draft').hidden=true;$('secret').value='';$('confirm').checked=false;
 digestPreview.textContent='';$('receipt').textContent='';receipt(null);updateControls();
 try{
  const project=me.projects.find(x=>x.id===p);
  if(!project)throw Error('企业空间不可用');
  let nextConfig=null,article=null,result=null;
  if(project.role==='owner'){
   nextConfig=await api(base+'/wechat');if(!current())return;
  }
  if(params.get('content')&&params.get('project')===p){
   const state=await api(base+'/state');if(!current())return;
   article=state.content.find(x=>x.id===params.get('content'));
   if(!article||String(article.revision)!==params.get('revision'))throw Error('文章版本已变化，请从工作台重新打开');
   result=await api(base+'/contents/'+encodeURIComponent(article.id)+'/wechat-draft');if(!current())return;
   if(result.revision!==article.revision)throw Error('文章版本已变化，请重新打开');
  }
  if(nextConfig){show(nextConfig);$('binding').hidden=false;}
  if(article){
   currentTemplate=result.template||null;importedSnapshot=!!result.imported_snapshot;
   templateInfo.textContent=currentTemplate?'默认排版：'+currentTemplate.name+' · v'+currentTemplate.version+'。后续公众号图文自动沿用；正文与配图按各篇内容替换。'+(importedSnapshot?'当前预览为从公众号回同步的已保存排版，原草稿继续保留。':''):'尚未设置公众号默认模板。可读取已保存草稿的排版作为后续模板。';
   targetBinding=result.binding||null;
   targetPreview.textContent=targetBinding?.appid?'本次目标公众号：'+(targetBinding.name||'未命名')+' · '+targetBinding.appid:'尚未绑定目标公众号，请先完成配置后刷新。';
   activeArticle={id:article.id,revision:article.revision};
   $('article').textContent=article.title+' · v'+article.revision;
   $('preview').href=base+'/contents/'+encodeURIComponent(article.id)+'/wechat-preview?revision='+article.revision;
   showDigest(result,article.revision);receipt(selectReceipt(result.records,targetBinding));
   const otherCount=result.records.filter(r=>r.appid!==targetBinding?.appid).length;
   if(otherCount)targetPreview.textContent+='。另有 '+otherCount+' 条其他公众号或未标明公众号的历史记录，未作为本次目标回执；原记录保留。';
   $('draft').hidden=false;
  }
  readyProject=p;$('status').textContent='企业：'+project.name;
 }catch(e){if(current())$('status').textContent=e.message;}
 finally{if(current()){loading=false;updateControls();}}
}

const labels={synced:'已同步；上次回读与提交版本一致',created:'已创建，等待回读核对',preparing:'正在准备；若服务中断请核对后再处理',sending:'正在提交；请等待或核对远端草稿',needs_review:'需要核对公众号草稿箱，禁止直接重发',failed:'同步失败，可检查原因后重试'};
function receipt(r){
 recoveryJob=r?.id||'';
 recoveryRequired=!!r&&unresolvedStatuses.includes(r.status);
 recoveryButton.hidden=!r||!['synced','preparing','sending','created','needs_review'].includes(r.status);
 recoveryButton.style.display=recoveryButton.hidden?'none':'';
 const checked=r?.synced_at?new Date(r.synced_at):null;
 const time=checked&&!Number.isNaN(checked.getTime())?' · 上次核对 '+checked.toLocaleString('zh-CN',{hour12:false}):'';
 $('receipt').textContent=r?(labels[r.status]||r.status)+' · v'+r.revision+(String(r.revision)!==params.get('revision')?'（历史版本）':'')+time+(r.media_id?' · 草稿编号 '+r.media_id:'')+(r.error?' · '+r.error:'')+(r.status==='synced'?'。这是历史回执；公众号内后续编辑、删除或发表不会自动回传。可重新核对，系统不会覆盖公众号内的修改。':''):'暂无同步记录';
}
function updateControls(){
 const ready=!accessBlocked&&!sessionPending&&!loading&&!busy&&readyProject===$('project').value;
 const role=me?.projects.find(x=>x.id===readyProject)?.role;
 const editable=ready&&['owner','editor'].includes(role)&&!!activeArticle;
 $('config-form').querySelector('button[type="submit"]').disabled=!(ready&&role==='owner'&&config);
 $('test').disabled=!(ready&&role==='owner'&&config?.has_secret);
 $('sync').disabled=!editable||importedSnapshot||recoveryRequired||!targetBinding?.appid||!targetBinding?.version;recoveryButton.disabled=!(editable&&recoveryJob);
 importButton.hidden=role!=='owner'||!activeArticle;importButton.disabled=!(editable&&role==='owner'&&recoveryJob&&targetBinding?.appid);
 $('project').disabled=busy||accessBlocked||sessionPending;
}
function suspendSession(){
 if(accessBlocked||!me)return;
 sessionPending=true;$('confirm').checked=false;$('secret').value='';updateControls();
}
async function verifySession(){
 if(accessBlocked||!me)return;
 if(sessionCheck)return sessionCheck;
 suspendSession();
 const previous=me;
 sessionCheck=(async()=>{
  try{
   const fresh=await api('/api/me');
   const roles=x=>JSON.stringify(x.projects.map(p=>[p.id,p.role]).sort((a,b)=>a[0].localeCompare(b[0])));
   if(!fresh.csrf||fresh.csrf!==previous.csrf||fresh.identity!==previous.identity||roles(fresh)!==roles(previous)){
    clearAccess();return;
   }
   sessionPending=false;
   if(!busy)$('status').textContent='登录状态已核验，请重新确认图文后操作。';
  }catch(e){
   if(!accessBlocked)$('status').textContent='暂时无法核验登录状态，操作已暂停。请恢复网络后重新切回此页。';
  }finally{sessionCheck=null;updateControls();}
 })();
 return sessionCheck;
}
if(typeof window!=='undefined'){
 window.addEventListener('focus',()=>{if(document.visibilityState!=='hidden')verifySession();});
 window.addEventListener('pageshow',e=>{if(e.persisted)verifySession();});
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')suspendSession();else verifySession();});
}
async function run(work){
 if(accessBlocked||sessionPending||busy||loading||!readyProject||readyProject!==$('project').value)return;
 busy=true;updateControls();
 try{await work();}catch(e){if(!accessBlocked)$('status').textContent=e.message;}
 finally{busy=false;updateControls();}
}

$('config-form').onsubmit=e=>{e.preventDefault();return run(async()=>{const secret=$('secret').value;$('secret').value='';show(await api(path()+'/wechat','PUT',{appid:$('appid').value.trim(),name:$('name').value.trim(),secret,version:config.version}));await load();if(readyProject)$('status').textContent='配置已加密保存，请测试连接并重新确认目标公众号。';});};
$('test').onclick=()=>run(async()=>{$('status').textContent='正在连接微信…';show(await api(path()+'/wechat/test','POST',{}));$('status').textContent='连接测试结束，结果见下方。';});
$('sync').onclick=()=>run(async()=>{
 if(recoveryRequired)throw Error('请先核对已有微信回执，不能直接重发');
 if(importedSnapshot)throw Error('此篇已回同步，请在原公众号草稿继续编辑');
 if(!targetBinding?.appid||!targetBinding?.version)throw Error('请先绑定公众号并刷新确认');
 if(!$('confirm').checked)throw Error('请先勾选图文确认');
 $('receipt').textContent='正在上传配图和创建草稿，请等待回执…';
 try{
  receipt(await api(path()+'/contents/'+encodeURIComponent(params.get('content'))+'/wechat-draft','POST',{revision:Number(params.get('revision')),confirm:true,appid:targetBinding.appid,binding_version:targetBinding.version,template_version:currentTemplate?.version||0}));
 }catch(e){
  if(accessBlocked)throw e;
  // A lost response can follow a successful remote write. Read local evidence only.
  await load();
  const refresh=readyProject?'已重新读取同步记录；请查看回执，系统未自动重发。':'同步记录也未能读取，请刷新页面核对后再操作。'+$('status').textContent;
  throw Error('未取得本次同步回执：'+e.message+'。'+refresh);
 }finally{$('confirm').checked=false;}
});
recoveryButton.onclick=()=>run(async()=>{if(!recoveryJob)throw Error('请重新读取同步记录');$('status').textContent='正在读取微信草稿进行核对，不会重新提交…';receipt(await api(path()+'/contents/'+encodeURIComponent(params.get('content'))+'/wechat-draft/'+encodeURIComponent(recoveryJob)+'/reconcile','POST',{}));$('status').textContent='回执核对完成';});
importButton.onclick=()=>run(async()=>{if(!recoveryJob||!targetBinding)throw Error('请先读取草稿回执');$('status').textContent='正在读取公众号保存的排版与图片，请稍候…';const result=await api(path()+'/contents/'+encodeURIComponent(params.get('content'))+'/wechat-draft/'+encodeURIComponent(recoveryJob)+'/import-layout','POST',{revision:Number(params.get('revision')),appid:targetBinding.appid,binding_version:targetBinding.version,make_default:true});await load();if(!accessBlocked)$('status').textContent='排版与 '+result.image_count+' 张图片已回同步，后续文章默认使用此模板。'+(result.warnings||[]).join('；');});
$('project').onchange=()=>{$('confirm').checked=false;load().catch(e=>$('status').textContent=e.message);};
(async()=>{try{me=await api('/api/me');for(const p of me.projects){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;$('project').append(o);}if(me.projects.some(p=>p.id===params.get('project')))$('project').value=params.get('project');await load();}catch(e){$('status').textContent=e.message;}})();
