'use strict';
const repurposeFormats=[['article','长媒体文章','问题解答 · 分节论证'],['xiaohongshu','小红书图文','封面 · 图卡 · 笔记'],['greenbook','小绿书图文','微信图文 · 轻量分享'],['moments','朋友圈','三个角度 · 配图建议'],['community','私域社群','分段分享 · 互动答疑'],['sales','私聊谈单','需求确认 · 异议回应'],['short_video','IP 短视频口播','口播 · 分镜 · AI画面提示词'],['live','直播分享稿','流程 · 口播 · 演示互动']];
const videoSkillFormats=[
 ['video_storyboard','导演分镜','把核心价值变成镜头','60秒分镜表 · 实景/示意素材清单','Seedance 分镜方法'],
 ['video_seedance','AI 画面设计','为每个镜头写清画面','运镜 · 光线 · 参考素材 · 连贯性','Seedance Prompt'],
 ['video_avatar','数字人口播','让讲解更像自然对话','逐字稿 · 重音停顿 · 形象与声音清单','HeyGen Avatar / Video'],
 ['video_edit','剪辑与动效','把素材排成完整时间线','剪辑点 · 转场 · 品牌标题 · 音画节奏','Remotion / HyperFrames'],
 ['video_captions','配音与字幕','准备可对齐的旁白与字幕','配音稿 · 发音词表 · 预估 SRT 字幕','本地字幕工作流'],
 ['video_translate','多语言视频','保留原意，面向海外受众','双语口播稿 · 术语表 · 字幕断句','HeyGen Translate']
];
repurposeFormats.push(...videoSkillFormats.map(([id,label,,desc])=>[id,label,desc]));
function repurposeUsesVideo(format){return ['short_video','live',...videoSkillFormats.map(x=>x[0])].includes(format);}

const repurposeDrafts=new Map(),repurposeSending=new Map(),repurposeRequests=new Map(),repurposeRestored=new Set(),repurposeStorageFailed=new Set();
const repurposeStoragePrefix='geo-repurpose-v1:',repurposeMaxAge=24*60*60*1000;
function repurposeScope(){return JSON.stringify([typeof me==='undefined'?'':me?.identity||'',pid]);}
function pruneRepurposeStorage(){
 try{for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(!key?.startsWith(repurposeStoragePrefix))continue;try{const r=JSON.parse(sessionStorage.getItem(key));if(r?.v!==1||!Number.isFinite(r.updated)||Date.now()-r.updated>repurposeMaxAge||r.updated>Date.now())sessionStorage.removeItem(key);}catch(_){sessionStorage.removeItem(key);}}}catch(_){}
}
function repurposeDraft(){
 const scope=repurposeScope();if(repurposeDrafts.has(scope))return repurposeDrafts.get(scope);
 let draft={source:'',topic:'',question:'',formats:['article','moments','short_video']};pruneRepurposeStorage();
 try{
  const raw=sessionStorage.getItem(repurposeStoragePrefix+scope);
  if(raw){
   if(raw.length>200000)throw Error('oversized session');
   const r=JSON.parse(raw),d=r.draft;
   if(r.v!==1||!Number.isFinite(r.updated)||Date.now()-r.updated>repurposeMaxAge||r.updated>Date.now()||typeof d?.source!=='string'||d.source.length>100||typeof d.question!=='string'||d.question.length>1000||!Array.isArray(d.formats)||d.formats.length>repurposeFormats.length||!d.formats.every(f=>repurposeFormats.some(x=>x[0]===f))||!Array.isArray(r.requests)||r.requests.length>100)throw Error('invalid session');
   for(const [signature,key] of r.requests){const parts=JSON.parse(signature);if(parts[0]!==scope||!Array.isArray(parts)||parts.length!==5||typeof key!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(key))throw Error('invalid request');}
   draft={source:d.source,topic:typeof d.topic==='string'?d.topic.slice(0,200):'',question:d.question,formats:[...new Set(d.formats)]};
   for(const [signature,key] of r.requests)repurposeRequests.set(signature,key);
   repurposeRestored.add(scope);
  }
 }catch(_){try{sessionStorage.removeItem(repurposeStoragePrefix+scope);}catch(_){} }
 repurposeDrafts.set(scope,draft);return draft;
}
function persistRepurpose(scope=repurposeScope()){
 const draft=repurposeDrafts.get(scope);if(!draft)return;
 const requests=[...repurposeRequests].filter(([signature])=>JSON.parse(signature)[0]===scope);
 try{sessionStorage.setItem(repurposeStoragePrefix+scope,JSON.stringify({v:1,updated:Date.now(),draft,requests}));repurposeStorageFailed.delete(scope);}catch(_){repurposeStorageFailed.add(scope);}
}
function repurposeRecoveryNote(){const scope=repurposeScope();return repurposeStorageFailed.has(scope)?'浏览器暂不能保存恢复信息；请勿刷新，先核对下方生成记录。':(repurposeRestored.has(scope)?'已恢复本标签页的原稿选择、传播目标和未完成选项；不会自动生成。':'本标签页会话中，刷新后可恢复未完成选择，最长保留24小时；退出登录清除。');}
function clearRepurposeSession(){
 if(typeof clearVideoSession==='function')clearVideoSession();
 ++repurposeRefreshTicket;
 repurposeSending.clear();repurposeDrafts.clear();repurposeEditors.clear();repurposeSaving.clear();repurposeRewriting.clear();repurposeFeedback.clear();repurposeRewriteKeys.clear();repurposeRequests.clear();repurposeRestored.clear();repurposeStorageFailed.clear();
 try{for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(key?.startsWith(repurposeStoragePrefix))sessionStorage.removeItem(key);}}catch(_){}
}

function repurposeAnswerUsable(j){return j?.payload?.workflow==='repurpose'&&j.status==='succeeded'&&!j.result?.discarded&&typeof j.result?.answer==='string'&&!!j.result.answer.trim();}
function repurposeResultBody(j){return repurposeAnswerUsable(j)?`<div class="expert-markdown">${expertMarkdown(j.result.answer)}</div>`:`<p role="status">${esc(j.result?.discarded?j.result.reason:j.error||(['queued','running'].includes(j.status)?'正在生成此形态的文案…':'任务未产生有效文案'))}</p>`;}
const repurposeEditors=new Map(),repurposeSaving=new Set(),repurposeRewriting=new Set(),repurposeFeedback=new Map(),repurposeRewriteKeys=new Map();
function repurposeEditKey(jobId){return JSON.stringify([repurposeScope(),jobId]);}
function repurposeInlineEditor(j,saved){const draft=repurposeEditors.get(repurposeEditKey(j.id));if(!draft)return '';return `<form class="repurpose-edit-form" data-job="${esc(j.id)}"><label>标题<input name="title" required maxlength="180" value="${esc(draft.title)}"></label><label>修改内容<textarea name="body" rows="14" required maxlength="40000">${esc(draft.body)}</textarea></label><p class="hint">编辑基于 v${draft.revision}；保存后仍为草稿，需重新审核。模型原始回复保留在执行记录。</p><button type="submit" class="primary" ${repurposeSaving.has(repurposeEditKey(j.id))?'disabled':''}>保存修改</button> ${action('取消修改','repurpose-cancel',j.id)}</form>`;}
function repurposeRewriteForm(j){const key=repurposeEditKey(j.id),busy=repurposeRewriting.has(key);return `<form class="repurpose-rewrite-form" data-job="${esc(j.id)}"><label>这份内容要怎么改<textarea name="feedback" rows="2" maxlength="1000" placeholder="例如：开头更直接，减少术语，保留盐雾数据和适用条件">${esc(repurposeFeedback.get(key)||'')}</textarea></label><button type="submit" class="small" ${busy||!canEdit()?'disabled':''}>${busy?'重新生成中…':'按意见重新生成这份'}</button></form>`;}
function repurposeResults(){return (state.execution||[]).filter(j=>j.payload?.workflow==='repurpose').map(j=>{const saved=state.content.find(c=>c.repurpose_job_id===j.id),editing=repurposeEditors.has(repurposeEditKey(j.id));return `<details class="source repurpose-result" open><summary>${esc(repurposeFormats.find(f=>f[0]===j.payload.repurpose_channel)?.[1]||'改编')} · ${esc(j.payload.core_topic||j.payload.repurpose_source?.title||'')} · ${esc(executionLabels[j.status]||j.status)}</summary><p class="hint">${j.payload.repurpose_source?'原稿 v'+j.payload.repurpose_source.revision:'核心选题'} · ${fmt(j.created)} · ${saved?'已保存稿 v'+saved.revision:'待审核文案'} · 只修改本份不会影响其他形态</p>${editing?repurposeInlineEditor(j,saved):(saved?`<h3>${esc(saved.title)}</h3><div class="expert-markdown">${expertMarkdown(saved.body)}</div>`:repurposeResultBody(j))}${!editing&&canEdit()&&repurposeAnswerUsable(j)?action(saved?'修改内容':'保存草稿并修改','repurpose-save',j.id):''}${!editing&&canEdit()&&repurposeAnswerUsable(j)?repurposeRewriteForm(j):''}</details>`;}).join('')||'<p class="hint">勾选内容形态后，每项会建立独立 Skill 任务；生成、重写、编辑和保存互不影响。</p>';}
function repaintRepurposeResults(project){if(pid===project&&page()==='repurpose'&&$('#repurpose-results'))$('#repurpose-results').innerHTML=repurposeResults();}
async function submitRepurposeRewrite(form){
 const project=pid,scope=repurposeScope(),session=repurposeEpoch(),jid=form.dataset.job,key=repurposeEditKey(jid),j=(state.execution||[]).find(x=>x.id===jid);
 const current=()=>pid===project&&repurposeScope()===scope&&repurposeEpoch()===session;
 if(!canEdit()||!repurposeAnswerUsable(j)||repurposeRewriting.has(key))return;
 const feedback=new FormData(form).get('feedback')?.trim();if(!feedback){toast('请填写本份修改意见');return;}
 const p=j.payload,format=p.repurpose_channel;
 const signature=JSON.stringify([key,feedback]);
 if(!repurposeRewriteKeys.has(signature))repurposeRewriteKeys.set(signature,crypto.randomUUID());
 repurposeRewriting.add(key);form.querySelector('button').disabled=true;
 try{
  await api(`/api/projects/${project}/execution/jobs`,'POST',{kind:'expert_chat',workflow:'repurpose',expert_id:repurposeUsesVideo(format)?'video':'content',skill_id:repurposeUsesVideo(format)?'video':'faq',
   resource_id:p.resource_id||'',core_topic:p.core_topic||'',source_revision:p.repurpose_source?.revision,repurpose_channel:format,repurpose_skill_id:'repurpose_'+format,
   question:p.question,rewrite_job_id:jid,rewrite_feedback:feedback,draft_reference:true,request_key:repurposeRewriteKeys.get(signature)});
  if(!current())return;
  repurposeRewriteKeys.delete(signature);
  if(current()){
   // An enqueue response may arrive after the user has typed their next edit.
   const currentFeedback=new FormData(form).get('feedback')||'';
   if(currentFeedback.trim()===feedback){repurposeFeedback.delete(key);form.reset();}
   else if(currentFeedback)repurposeFeedback.set(key,currentFeedback);
   else repurposeFeedback.delete(key);
   repurposeRewriting.delete(key);
   await refresh();if(current()){repaintRepurposeResults(project);toast('已单独提交重写，原结果保留；其他内容不变');}
  }
 }catch(ex){if(current())toast(ex.message);}
 finally{if(repurposeEpoch()===session){repurposeRewriting.delete(key);if(form.isConnected)form.querySelector('button').disabled=false;}}
}
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-action="repurpose-preferences"]');if(!b)return;const format=b.dataset.id;
 const saved=(state.format_skill||[]).find(x=>x.format===format),label=repurposeFormats.find(x=>x[0]===format)?.[1];if(!label)return;
 const project=pid,scope=repurposeScope(),session=repurposeEpoch();
 const current=()=>pid===project&&scope===repurposeScope()&&session===repurposeEpoch();
 openModal(label+' · 默认写作要求',`<form><label>以后这一类内容怎么写<textarea name="requirements" rows="8" maxlength="3000" ${canEdit()?'':'readonly'} placeholder="语气、长度、开头方式、结构、避免使用的表达">${esc(saved?.requirements||'')}</textarea></label><p class="hint">只影响当前企业以后生成的「${esc(label)}」。不会重写已有内容或其他形态；留空恢复默认规则。本次微调请使用结果下方的修改意见。</p>${err()}${canEdit()?'<button type="submit" class="primary">保存这类内容的默认要求</button>':''}</form>`,false,async f=>{
  if(!current()||!canEdit())throw Error('账号、企业或权限已变化，请重新打开写作要求');
  await api(`/api/projects/${project}/format-skills/${format}`,'PUT',{version:saved?.version||0,requirements:f.get('requirements')});
  if(current()){closeModal();await refresh();if(current())toast('已保存本形态默认要求，已有稿件保留');}
 });
});
function repurposePage(){const d=repurposeDraft(),busy=repurposeSending.has(pid);return head('一鱼多吃','一个核心选题，勾选需要的内容形态；每项建立独立 Skill，可单独重写和修改。')+`<form id="repurpose-form"><section class="panel"><p id="repurpose-recovery" class="hint" role="status">${esc(repurposeRecoveryNote())}</p><h2>1. 确定核心选题</h2><label>核心选题<input name="topic" maxlength="200" value="${esc(d.topic||'')}" placeholder="例如：为什么喷涂返锈，往往要先排查前处理？"></label><label>参考原稿（可选）<select name="source"><option value="">从核心选题与企业知识独立创作</option>${state.content.filter(c=>c.status!=='generating'&&c.body).map(c=>`<option value="${esc(c.id)}" ${d.source===c.id?'selected':''}>${esc(c.title)} · v${c.revision}</option>`).join('')}</select></label><label>本次传播目标<textarea name="question" rows="2" maxlength="1000" placeholder="例如：面向汽车零部件采购负责人，说明选择前处理方案时应核对的条件">${esc(d.question)}</textarea></label><h2>2. 勾选要生成的内容</h2><p class="hint">每项使用独立写作规则；可单独修改默认要求，生成后也可只重写其中一份。</p><div class="repurpose-formats">${repurposeFormats.slice(0,8).map(([id,label,desc])=>`<div class="repurpose-skill-card"><label class="repurpose-option"><input type="checkbox" name="formats" value="${id}" ${d.formats.includes(id)?'checked':''}><span><strong>${label}</strong><small>${desc}</small></span></label>${action('写作要求','repurpose-preferences',id,'class="small"')}</div>`).join('')}</div></section><section class="panel repurpose-submit"><p class="hint">每个勾选项独立调用对应 Skill；提交后可单独按意见重写或进入编辑。修改一份不会影响其他形态。原稿或来源更新后，旧结果不能保存为新稿。</p>${err()}<button type="submit" class="primary" ${busy||!canEdit()?'disabled':''}>${busy?'正在提交…':'生成所选文案'}</button></section></form>`+panel('生成结果与修改','每份结果都是独立稿件；可单独修改、重写和保存。',`<div id="repurpose-results">${repurposeResults()}</div>`)+(typeof videoComposerPanel==='function'?videoComposerPanel():'');}
document.addEventListener('input',e=>{if(e.target.closest?.('#repurpose-form')&&['question','topic'].includes(e.target.name)){repurposeDraft()[e.target.name]=e.target.value;persistRepurpose();}const rewrite=e.target.closest?.('.repurpose-rewrite-form');if(rewrite&&e.target.name==='feedback'){const key=repurposeEditKey(rewrite.dataset.job);if(e.target.value)repurposeFeedback.set(key,e.target.value);else if(repurposeFeedback.delete(key))refresh().catch(()=>{});}});
document.addEventListener('change',e=>{if(!e.target.closest?.('#repurpose-form'))return;const d=repurposeDraft();if(e.target.name==='source')d.source=e.target.value;if(e.target.name==='formats')d.formats=Array.from($('#repurpose-form').querySelectorAll('[name="formats"]:checked')).map(x=>x.value);persistRepurpose();});
function syncRepurposeForm(project){
 if(pid!==project||page()!=='repurpose')return;
 const form=$('#repurpose-form');if(!form)return;
 const busy=repurposeSending.has(project),d=repurposeDraft();
 const notice=form.querySelector('#repurpose-recovery');if(notice)notice.textContent=repurposeRecoveryNote();
 for(const input of form.querySelectorAll('[name="formats"]')){input.checked=d.formats.includes(input.value);input.disabled=busy||!canEdit();}
 for(const input of form.querySelectorAll('[name="source"],[name="question"],[name="topic"]'))input.disabled=busy||!canEdit();
 const button=form.querySelector('button[type="submit"]');if(button){button.disabled=busy||!canEdit();button.textContent=busy?'正在提交…':'生成所选文案';}
}
document.addEventListener('submit',e=>{
 if(e.target.id!=='repurpose-form')return;e.preventDefault();const project=pid,scope=repurposeScope(),session=repurposeEpoch(),batch={};
 const current=()=>project===pid&&scope===repurposeScope()&&session===repurposeEpoch();
 if(!canEdit()||repurposeSending.has(project))return;
 repurposeSending.set(project,batch);
 formSubmit(e.target,async f=>{
  const formats=f.getAll('formats');if(!formats.length)throw Error('至少选择一种内容形态');
  // Read form values before disabling inputs; retain one key for uncertain HTTP outcomes.
  const source=f.get('source')||'',topic=f.get('topic')?.trim()||'',question=f.get('question')?.trim()||'保留原稿的价值和事实，按目标场景重新组织内容。';
  if(!source&&!topic)throw Error('请输入核心选题或选择参考原稿');
  const revision=state.content.find(c=>c.id===source)?.revision;
  const draft=repurposeDraft();draft.source=source;draft.topic=topic;draft.question=f.get('question')||'';draft.formats=[...formats];persistRepurpose(scope);syncRepurposeForm(project);let sent=0;
  for(const format of formats){
   if(!current())return;
   const signature=JSON.stringify([scope,source,revision,JSON.stringify([topic,question]),format]);
   if(!repurposeRequests.has(signature))repurposeRequests.set(signature,crypto.randomUUID());
   persistRepurpose(scope);syncRepurposeForm(project);
   try{
    await api(`/api/projects/${project}/execution/jobs`,'POST',{kind:'expert_chat',workflow:'repurpose',expert_id:repurposeUsesVideo(format)?'video':'content',skill_id:repurposeUsesVideo(format)?'video':'faq',resource_id:source,core_topic:topic,source_revision:revision,auto_knowledge:!source,repurpose_channel:format,repurpose_skill_id:'repurpose_'+format,question,draft_reference:true,request_key:repurposeRequests.get(signature)});
    if(!current())return;
    sent++;draft.formats=draft.formats.filter(x=>x!==format);repurposeRequests.delete(signature);persistRepurpose(scope);syncRepurposeForm(project);
   }catch(ex){
    if(!current())return;
    try{await refresh();}catch(_){}if(!current())return;
    throw Error(`已确认提交 ${sent} 项；未完成选项已保留，可重试。${ex.message}`);
   }
  }
  if(current()){await refresh();if(current())toast(`已提交 ${sent} 项独立生成任务；已提交形态已取消勾选`);}
 }).finally(()=>{if(repurposeSending.get(project)===batch){repurposeSending.delete(project);syncRepurposeForm(project);}});
});
document.addEventListener('click',async e=>{
 const cancel=e.target.closest('[data-action="repurpose-cancel"]');if(cancel){e.preventDefault();const key=repurposeEditKey(cancel.dataset.id);if(!repurposeSaving.has(key)){repurposeEditors.delete(key);repaintRepurposeResults(pid);}return;}
 const b=e.target.closest('[data-action="repurpose-save"]');if(!b)return;
 const j=(state.execution||[]).find(x=>x.id===b.dataset.id);if(!canEdit()||!repurposeAnswerUsable(j)){toast('请等待有效文案完成后再保存');return;}
 const project=pid,scope=repurposeScope(),session=repurposeEpoch(),key=repurposeEditKey(j.id);if(repurposeSaving.has(key))return;repurposeSaving.add(key);b.disabled=true;
 const current=()=>pid===project&&scope===repurposeScope()&&session===repurposeEpoch();
 try{let saved=state.content.find(c=>c.repurpose_job_id===j.id);if(!saved){const r=await api(`/api/projects/${project}/repurpose/from-job/${encodeURIComponent(j.id)}`,'POST',{});if(!current())return;await refresh();if(!current())return;saved=state.content.find(c=>c.id===r.id);}
 if(!current())return;if(!saved)throw Error('草稿未加载，请刷新后重试');
 repurposeEditors.set(key,{id:saved.id,title:saved.title,body:saved.body,revision:saved.revision,channels:saved.channels||[],scheduled:saved.scheduled||''});repaintRepurposeResults(project);
 }catch(ex){if(current())toast(ex.message);}finally{if(session===repurposeEpoch()){repurposeSaving.delete(key);if(b.isConnected)b.disabled=false;if(current())repaintRepurposeResults(project);}}
});
document.addEventListener('input',e=>{const form=e.target.closest?.('.repurpose-edit-form');if(!form||!['title','body'].includes(e.target.name))return;const draft=repurposeEditors.get(repurposeEditKey(form.dataset.job));if(draft)draft[e.target.name]=e.target.value;});
document.addEventListener('submit',e=>{
 if(e.target.matches?.('.repurpose-rewrite-form')){e.preventDefault();submitRepurposeRewrite(e.target);return;}
 if(!e.target.matches?.('.repurpose-edit-form'))return;e.preventDefault();const project=pid,scope=repurposeScope(),session=repurposeEpoch(),key=repurposeEditKey(e.target.dataset.job),draft=repurposeEditors.get(key);
 const current=()=>pid===project&&scope===repurposeScope()&&session===repurposeEpoch();
 if(!draft||!canEdit()||repurposeSaving.has(key))return;repurposeSaving.add(key);
 formSubmit(e.target,async()=>{try{
  const {id,...body}=draft;await api(`/api/projects/${project}/contents/${encodeURIComponent(id)}`,'PUT',body);
  if(!current())return;
  const live=repurposeEditors.get(key),changed=live&&live===draft&&(live.title!==body.title||live.body!==body.body);
  if(changed)live.revision=body.revision+1;
  else if(live===draft)repurposeEditors.delete(key);
  repurposeSaving.delete(key);
  await refresh();if(current()){repaintRepurposeResults(project);toast(changed?'已保存提交时的版本；刚补充的文字已保留，请再次保存':'修改已保存，仍为待审核草稿');}
 }finally{if(session===repurposeEpoch())repurposeSaving.delete(key);}});
});
const repurposeBaseRefresh=refresh;
let repurposeRefreshTicket=0;
function repurposeEpoch(){return typeof epoch==='undefined'?0:epoch;}
refresh=async function(){
 if(page()!=='repurpose'||!$('#repurpose-form'))return repurposeBaseRefresh();
 const project=pid,scope=repurposeScope(),session=repurposeEpoch(),ticket=++repurposeRefreshTicket;
 const current=()=>pid===project&&scope===repurposeScope()&&session===repurposeEpoch()&&ticket===repurposeRefreshTicket&&page()==='repurpose';
 let next;
 try{next=await api(`/api/projects/${project}/state`);}catch(ex){if(!current())return;throw ex;}
 if(!current())return;
 state=next;
 const results=$('#repurpose-results');
 if(results&&![...repurposeEditors.keys(),...repurposeFeedback.keys()].some(k=>JSON.parse(k)[0]===scope))results.innerHTML=repurposeResults();
 syncRepurposeForm(project);syncManager();
};
