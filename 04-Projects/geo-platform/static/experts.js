'use strict';
// A deliberately small presentation subset: model text never supplies HTML,
// URL attributes, images, embeds or language classes to the DOM.
function expertInline(value){
  const text=String(value),tokens=/`([^`\n]+)`|\*\*([^*\n]+)\*\*/g;
  let out='',from=0,match;
  while((match=tokens.exec(text))){out+=esc(text.slice(from,match.index));out+=match[1]!==undefined?`<code>${esc(match[1])}</code>`:`<strong>${esc(match[2])}</strong>`;from=tokens.lastIndex;}
  return out+esc(text.slice(from));
}
function expertTableCells(line){
  let text=line.trim();if(!text.includes('|'))return null;
  if(text.startsWith('|'))text=text.slice(1);
  if(text.endsWith('|')&&!text.endsWith('\\|'))text=text.slice(0,-1);
  const cells=[];let cell='';
  for(let i=0;i<text.length;i++){
    if(text[i]==='\\'&&text[i+1]==='|'){cell+='|';i++;}
    else if(text[i]==='|'){cells.push(cell.trim());cell='';}
    else cell+=text[i];
  }
  cells.push(cell.trim());return cells.length>=2&&cells.length<=12?cells:null;
}
function expertMarkdown(value){
  const lines=String(value??'').replace(/\r\n?/g,'\n').split('\n'),out=[];
  let paragraph=[],list=null,fence=null,code=[];
  const flushParagraph=()=>{if(paragraph.length){out.push('<p>'+paragraph.map(expertInline).join('<br>')+'</p>');paragraph=[];}};
  const flushList=()=>{if(list){out.push(`<${list.type}>`+list.items.map(item=>`<li${item.number!==null?` value="${item.number}"`:''}>${item.lines.map(expertInline).join('<br>')}</li>`).join('')+`</${list.type}>`);list=null;}};
  const flush=()=>{flushParagraph();flushList();};
  const flushCode=()=>{out.push('<pre><code>'+esc(code.join('\n'))+'</code></pre>');code=[];fence=null;};
  for(let index=0;index<lines.length;index++){
    const line=lines[index];
    if(fence){const end=line.trim();if(new RegExp('^'+fence.char+'{'+fence.length+',}\\s*$').test(end))flushCode();else code.push(line);continue;}
    const open=line.match(/^\s{0,3}(`{3,}|~{3,})(.*)$/);
    if(open){flush();fence={char:open[1][0],length:open[1].length};continue;}
    if(!line.trim()){flush();continue;}
    const columns=expertTableCells(line),separator=expertTableCells(lines[index+1]||'');
    if(columns&&separator&&columns.length===separator.length&&separator.every(cell=>/^:?-{3,}:?$/.test(cell))){
      flush();const rows=[];index++;
      while(index+1<lines.length){const row=expertTableCells(lines[index+1]);if(!row||row.length!==columns.length)break;rows.push(row);index++;}
      out.push('<div class="expert-table-scroll" role="region" aria-label="内容表格" tabindex="0"><table><thead><tr>'+columns.map(cell=>'<th scope="col">'+expertInline(cell)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(cell=>'<td>'+expertInline(cell)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>');continue;
    }
    const heading=line.match(/^\s{0,3}(#{1,6})\s+(.+)$/);
    if(heading){flush();const level=Math.min(5,heading[1].length+2);out.push(`<h${level}>${expertInline(heading[2])}</h${level}>`);continue;}
    const item=line.match(/^\s{0,3}(?:(\d{1,6})[.)、]|([-+*]))\s+(.+)$/);
    if(item){flushParagraph();const type=item[1]?'ol':'ul';if(list&&list.type!==type)flushList();if(!list)list={type,items:[]};list.items.push({number:item[1]?Number(item[1]):null,lines:[item[3]]});continue;}
    if(list&&/^\s{2,}\S/.test(line)){list.items[list.items.length-1].lines.push(line.trim());continue;}
    const quote=line.match(/^\s{0,3}>\s?(.*)$/);
    if(quote){flush();out.push('<blockquote>'+expertInline(quote[1])+'</blockquote>');continue;}
    flushList();paragraph.push(line);
  }
  if(fence)flushCode();flush();return out.join('');
}
// Unsent text and Skill choices are private to the account, enterprise and expert.
let activeExpert='content';
let expertShowAll=false;
const expertGuides={
 strategist:{goal:'把核心问题变成有先后顺序的内容计划',output:'问题簇 · 选题优先级 · 证据清单',tasks:[['规划选题','围绕【核心问题】，面向【目标客户】规划5个选题，说明优先级、核心主张和需要补齐的证据。'],['制定月度计划','围绕【核心主题】做一份月度内容建议，按客户决策阶段安排顺序，说明每篇解决什么问题。']]},
 content:{goal:'从一个客户问题，写到一篇完整文章',output:'标题角度 · 文章提纲 · 可编辑正文',tasks:[['写一篇文章','围绕【核心问题】，结合企业资料写一篇完整文章，开头直接回应客户疑问，结尾给出可执行的下一步。'],['先看选题与提纲','围绕【核心问题】给出3个不同角度的标题，推荐一个并展开提纲，标明各节需要的证据。']]},
 technical:{goal:'把技术机制讲清楚，把适用条件写完整',output:'技术指南 · 条件对比 · 验收清单',tasks:[['写技术指南','解释【产品或工艺】在【应用工况】中的选择方法，写清机制、适用条件、验证和验收要求。'],['对比两个方案','围绕【方案A】和【方案B】，按相同工况与验收维度进行对比，没有依据的数据列为待提供。']]},
 seo_editor:{goal:'让答案更清楚，让证据更容易被找到',output:'标题与摘要 · 问题式结构 · 引用建议',tasks:[['优化文章结构','请优化下面文章的标题、开篇直接回答、小节与FAQ，保留事实和来源编号：\n【粘贴原文】'],['检查引用与问答','围绕【客户问题】检查当前内容的答案完整度与证据缺口，给出可直接使用的问答建议。']]},
 video:{goal:'把一个观点，变成能拍摄的分镜与口播',output:'开场钩子 · 分镜表 · 口播与素材需求',tasks:[['写60秒脚本','围绕【核心问题】写一份约60秒的视频脚本，给出逐镜时间、画面、口播、字幕与素材需求。'],['改进开场与节奏','请改进下面脚本的前3秒开场和叙事节奏，保留原有事实，给出完整新版：\n【粘贴脚本】']]},
 reviewer:{goal:'找到具体问题，并给出能直接替换的写法',output:'分级问题 · 依据核对 · 替换文案',tasks:[['逐句审校','审校下面内容，按必改、建议、待提供分级，逐项给出原句、问题、依据和替换文字：\n【粘贴原文】'],['检查承诺与数字','检查下面内容中的性能承诺、参数、认证、案例及其适用条件，指出无依据的表达：\n【粘贴原文】']]}
};
function routeExpert(){const id=new URLSearchParams(location.hash.split('?')[1]||'').get('expert');return contentExperts.some(e=>e[0]===id)?id:'';}
const expertDrafts=new Map();
const expertSending=new Map();
let expertSessionGeneration=0;
function clearExpertSession(){
 ++expertSessionGeneration;++expertRefreshTicket;
 expertDrafts.clear();expertSending.clear();expertShowAll=false;
}
function isExpertChat(job){return job.job_type==='expert_chat'&&['chat',undefined].includes(job.payload?.workflow);}
function isVisibleExpertChat(job){return isExpertChat(job)&&!/^\s*[【\[]本机功能验收[】\]]/.test(job.payload?.question||'');}
function expertBusy(expert=activeExpert){return expertSending.has(expertKey(expert))||(state.execution||[]).some(j=>isExpertChat(j)&&j.payload.expert_id===expert&&['queued','running'].includes(j.status));}
function expertAnswerUsable(job){return isExpertChat(job)&&job.status==='succeeded'&&!job.result?.discarded&&typeof job.result?.answer==='string'&&!!job.result.answer.trim();}
function expertKey(expert=activeExpert){return JSON.stringify([me?.identity||'',pid,expert]);}
function expertDraft(){if(!expertDrafts.has(expertKey()))expertDrafts.set(expertKey(),{text:'',brief:{},revise:'',skill:contentExperts.find(e=>e[0]===activeExpert)?.[4]||'faq'});return expertDrafts.get(expertKey());}
function expertAvatar(id){return `<img class="expert-avatar" src="/static/experts/${id}-portrait-v1.webp?v=20261003-40" alt="${esc(contentExperts.find(e=>e[0]===id)?.[1]||'专家')} AI 头像">`;}
expertStrip=function(){return `<section class="expert-section expert-catalog"><div class="expert-catalog-intro"><h2>这次，你想完成什么？</h2><p>选一位专家，从一个核心问题开始。成果可以继续修改，再保存为稿件。</p></div><div class="expert-grid">${contentExperts.map(([id,name])=>{const g=expertGuides[id];return `<a class="expert-card" href="#skills?expert=${id}"><div class="expert-card-heading">${expertAvatar(id)}<h3>${esc(name)}</h3></div><p>${g.goal}</p><span class="expert-deliverable">${g.output}</span><span class="expert-card-cta">开始${id==='reviewer'?'审校':id==='video'?'写脚本':id==='strategist'?'策划':'创作'} <span aria-hidden="true">→</span></span></a>`;}).join('')}</div><p class="expert-catalog-note">同一企业的资料与当前用户的需求可以跨专家联动；每位专家保留独立对话。</p></section>`;};
function expertContextNote(payload){const c=payload.context_selection;if(c?.mode!=='excerpts')return '';return `<p class="hint">本次仅提供相关原文及相邻段落：${esc(c.sent_chars)} / ${esc(c.original_chars)} 字符（资料正文）。未传全文；未覆盖的事实需补充资料。完整来源快照保留用于版本校验。</p>`;}
function expertChatRows(){return (state.execution||[]).filter(j=>isVisibleExpertChat(j)&&j.payload.expert_id===activeExpert);}
function expertHistoryButton(){return !expertShowAll&&expertChatRows().length>30?`<div class="expert-history-load">${action('查看更早的对话','expert-history-all')}</div>`:'';}
function expertConversation(){const rows=(state.execution||[]).filter(j=>isVisibleExpertChat(j)&&j.payload.expert_id===activeExpert).slice(0,expertShowAll?undefined:30).reverse();return rows.length?rows.map(j=>`<section class="expert-turn"><div class="expert-question"><p>${esc(j.payload.question)}</p></div><div class="expert-answer"><div class="between"><strong>${esc(contentExperts.find(e=>e[0]===activeExpert)[1])}</strong><span class="hint">${esc(executionLabels[j.status]||j.status)} · ${fmt(j.created)}</span></div>${expertAnswerUsable(j)?`<div class="expert-markdown">${expertMarkdown(j.result.answer)}</div>`:`<p role="status">${esc(j.result?.discarded?j.result.reason:j.error||(['queued','running'].includes(j.status)?'专家正在处理，回复会自动出现在这里。':'任务未产生回复'))}</p>`}<details><summary>本次资料来源 ${j.payload.sources?.length||0} 份</summary>${expertContextNote(j.payload)}${(j.payload.sources||[]).map(s=>`<p class="hint">${esc(s.title)} · v${s.version} · ${s.status==='confirmed'?'已核准':'待事实核准'}</p>`).join('')||'<p class="hint">本次仅提供通用策划建议，没有匹配到企业资料。</p>'}</details>${expertBriefNote(j.payload)}${expertAnswerUsable(j)&&canEdit()? `<div class="expert-answer-actions">${action('修改这条回复','expert-revise',j.id,'class="small"')} ${action('继续编辑图文','expert-compose',j.id,'class="small"')}</div>`:''}</div></section>`).join(''):`<div class="expert-welcome"><h3>有什么可以帮你？</h3></div>`;}
function expertBriefNote(payload){const rows=[['audience','受众'],['channel','渠道'],['tone','风格'],['length','篇幅 / 时长']].filter(([key])=>payload.chat_brief?.[key]);return rows.length?`<details><summary>本次写作要求</summary>${rows.map(([key,label])=>`<p class="hint">${label}：${esc(payload.chat_brief[key])}</p>`).join('')}</details>`:'';}
function expertRevisionNote(){const d=expertDraft(),j=(state.execution||[]).find(x=>x.id===d.revise);return j?`<div class="expert-revision-note" role="status"><b>正在修改指定回复</b><p>${esc(j.payload.question.slice(0,120))}</p><small>原回复保留；在下方写明希望改哪里。</small>${action('取消指定修改','expert-revise-cancel','','class="small"')}</div>`:'';}
function expertWorkspace(){const d=expertDraft(),expert=contentExperts.find(e=>e[0]===activeExpert),busy=expertBusy();setTimeout(()=>{const box=$('#expert-conversation');if(box)box.scrollTop=box.scrollHeight;},0);return `<section class="expert-workspace expert-chat-layout"><header><a href="#skills" aria-label="返回全部内容专家" class="expert-back">←</a><div class="expert-identity">${expertAvatar(activeExpert)}<h2>${expert[1]}</h2></div></header><div id="expert-conversation" aria-live="polite">${expertHistoryButton()}${expertConversation()}</div><form id="expert-chat-form"><input type="hidden" name="skill_id" value="${esc(d.skill)}"><div id="expert-revision-note">${expertRevisionNote()}</div><div class="expert-chat-input"><textarea id="expert-message" name="question" aria-label="发送消息" rows="2" maxlength="1000" required placeholder="发消息，聊聊你的想法…">${esc(d.text)}</textarea><button class="primary" type="submit" aria-label="发送消息" ${!canEdit()||busy?'disabled':''}>${busy?'专家处理中…':'发送给专家'}</button></div>${err()}</form></section>`;}
skillsPage=function(){const selected=routeExpert();if(selected){activeExpert=selected;return expertWorkspace();}return head('内容专家','选择一位专家，开始对话。')+expertStrip();};
document.addEventListener('input',e=>{if(e.target.id==='expert-message')expertDraft().text=e.target.value;if(e.target.dataset?.expertBrief){const d=expertDraft();(d.brief??={})[e.target.dataset.expertBrief]=e.target.value;}});
document.addEventListener('change',e=>{if(e.target.closest?.('#expert-chat-form')&&e.target.name==='skill_id')expertDraft().skill=e.target.value;});
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b)return;if(b.dataset.action==='expert-open'){if(!contentExperts.some(x=>x[0]===b.dataset.id))return;activeExpert=b.dataset.id;expertShowAll=false;location.hash='skills?expert='+activeExpert;render();}if(b.dataset.action==='expert-compose'){saveExpertDraft(b.dataset.id,b);}});
document.addEventListener('submit',e=>{
 if(e.target.id!=='expert-chat-form')return;e.preventDefault();
 const project=pid,expert=activeExpert,draft=expertDraft(),form=e.target,key=expertKey(expert);
 if(!canEdit()||expertBusy(expert))return;
 const current=expertSessionCurrent(),token={},textAtSend=draft.text,reviseAtSend=draft.revise||'';
 const visible=()=>current()&&page()==='skills'&&activeExpert===expert&&form.isConnected;
 expertSending.set(key,token);
 formSubmit(form,async f=>{
  try{
   const question=f.get('question').trim();if(!question)throw Error('请输入需求');
   if(/【(?:核心问题|目标客户|核心主题|产品或工艺|应用工况|方案A|方案B|粘贴原文|客户问题|粘贴脚本)】/.test(question))throw Error('请先把【】里的示例替换为你的实际问题或原文');
   if(f.getAll('reference_modules').length>8)throw Error('一次最多选用8个内容模块');
   await api(`/api/projects/${project}/execution/jobs`,'POST',{kind:'expert_chat',expert_id:expert,skill_id:f.get('skill_id'),question,chat_brief:{},revise_job_id:reviseAtSend,auto_knowledge:true,draft_reference:true,reference_ids:f.getAll('reference_ids').filter(Boolean),reference_modules:f.getAll('reference_modules').map(x=>JSON.parse(x))});
   if(!current())return;
   if(draft.text===textAtSend){if(draft.revise===reviseAtSend){draft.revise='';if(visible()&&$('#expert-revision-note'))$('#expert-revision-note').innerHTML='';}draft.text='';if(visible()&&$('#expert-message'))$('#expert-message').value='';}
   if(!visible())return;
   await refresh();if(visible()){const box=$('#expert-conversation');if(box)box.scrollTop=box.scrollHeight;}
  }catch(ex){if(visible())throw ex;}
 }).finally(()=>{
  if(expertSending.get(key)===token)expertSending.delete(key);
  if(visible()){
   const button=form.querySelector('button[type=submit]');
   if(button){const busy=expertBusy(expert);button.disabled=!canEdit()||busy;button.textContent=busy?'专家处理中…':'发送给专家';}
  }
 });
});

jobNames.expert_chat='专家 Skill 对话';jobNames.intent_plan='客户意图分析';
function creationPlan(){const j=(state.execution||[]).find(x=>x.id===creation?.planJobId);if(!j)return '';return `<section class="panel"><h3>AI 意图分析</h3><p class="hint">${esc(executionLabels[j.status])} · 策划建议，不是搜索量或市场调研数据</p><div class="text-body">${esc(j.result?.analysis||j.result?.reason||j.error||'正在分析客户角色、购买阶段与内容方向…')}</div></section>`;}
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action="creation-analyze"]');if(!b)return;const project=pid,session=creation,f=$('#creation-form');try{const keyword=f.querySelector('[name="keyword"]').value.trim(),question=f.querySelector('[name="customer_question"]').value.trim();if(!keyword||!question)throw Error('请填写关键词和客户问题');b.disabled=true;session.keyword=keyword;session.customer_question=question;const r=await api(`/api/projects/${project}/execution/jobs`,'POST',{kind:'intent_plan',keyword,question});if(pid!==project||creation!==session)return;creation.planJobId=r.id;await refresh();}catch(ex){toast(ex.message);}finally{b.disabled=false;}});

// Refresh only the reply area while an expert is composing; do not destroy typed input.
const expertBaseRefresh=refresh;
let expertRefreshTicket=0;
function expertSessionCurrent(){
 const project=pid,identity=me?.identity,session=epoch,generation=expertSessionGeneration;
 return ()=>project===pid&&identity===me?.identity&&session===epoch&&generation===expertSessionGeneration;
}
refresh=async function(){
 if(page()!=='skills'||!$('#expert-chat-form'))return expertBaseRefresh();
 const project=pid,current=expertSessionCurrent(),expert=activeExpert,ticket=++expertRefreshTicket;
 const valid=()=>current()&&ticket===expertRefreshTicket&&page()==='skills'&&expert===activeExpert&&!!$('#expert-chat-form');
 let next;
 try{next=await api(`/api/projects/${project}/state`);}catch(ex){if(!valid())return;throw ex;}
 if(!valid())return;
 state=next;
 const conversation=$('#expert-conversation'),atBottom=conversation.scrollHeight-conversation.scrollTop-conversation.clientHeight<80;
 const markup=expertHistoryButton()+expertConversation();
 if(conversation.dataset?.renderedMarkup!==markup){
  const previousTop=conversation.scrollTop;
  const opened=[...(conversation.querySelectorAll?.('details')||[])].map((el,index)=>el.open?index:-1).filter(index=>index>=0);
  conversation.innerHTML=markup;if(conversation.dataset)conversation.dataset.renderedMarkup=markup;
  const details=conversation.querySelectorAll?.('details')||[];for(const index of opened)if(details[index])details[index].open=true;
  conversation.scrollTop=atBottom?conversation.scrollHeight:previousTop;
 }
 const button=$('#expert-chat-form button[type="submit"]');
 if(button){const busy=expertBusy();button.disabled=!canEdit()||busy;button.textContent=busy?'专家处理中…':'发送给专家';}
 syncManager();
};

document.addEventListener('keydown',e=>{if(e.target.id!=='expert-message'||e.key!=='Enter'||e.shiftKey||e.isComposing||e.keyCode===229)return;e.preventDefault();const form=e.target.closest('form'),button=form?.querySelector('button[type="submit"]');if(button&&!button.disabled)form.requestSubmit();});

contentPage=function(){return head('图文编辑与稿件','查看已有稿件，编辑图文并提交审核。',action('找专家创作','navigate','skills'))+panel('内容工作流',`${state.content.length} 篇 · 草稿 → 排版 → 客户审核 → 发布交付`,state.content.length?contentTable(state.content):empty('暂无稿件','先与内容专家沟通，再将回复保存为草稿。'));};
compose=function(){closeModal();location.hash='skills?expert=content';render();};

function expertMemoryPanel(){const rows=(state.execution||[]).filter(j=>isVisibleExpertChat(j)&&j.payload.expert_id===activeExpert);return `<details class="panel"><summary>对话记录与联动记忆 · 本专家 ${rows.length} 次对话</summary><p class="hint">对话长期保存在本企业。每次回复会调用本专家最近有效对话，以及你在各专家处提出的近期需求、相关历史和表达偏好；不会带入其他企业的内容。</p>${rows.length>30&&!expertShowAll?action('查看全部历史对话','expert-history-all'):''}</details>`;}
document.addEventListener('click',e=>{if(e.target.closest('[data-action="expert-history-all"]')){const box=$('#expert-conversation');if(!box)return;const height=box.scrollHeight,top=box.scrollTop;expertShowAll=true;box.innerHTML=expertConversation();box.scrollTop=box.scrollHeight-height+top;if(box.dataset)box.dataset.renderedMarkup=box.innerHTML;}});

function expertReferenceSelection(){const selected=new URLSearchParams(location.hash.split('?')[1]||'').get('reference');return `<label>复用爆款库方法（可选）<select name="reference_ids"><option value="">不指定</option>${(state.content_reference||[]).map(r=>`<option value="${esc(r.id)}" ${r.id===selected?'selected':''}>${esc(r.title)}</option>`).join('')}</select></label>`;}

async function saveExpertDraft(id,button){
 const project=pid,current=expertSessionCurrent(),expert=activeExpert,route=location.hash;
 const valid=()=>current()&&activeExpert===expert&&location.hash===route;
 const job=(state.execution||[]).find(j=>j.id===id);
 if(!canEdit()||!job||!expertAnswerUsable(job)){toast('此回复不可保存，请使用已完成的有效专家回复');return;}
 button.disabled=true;
 try{
  const r=await api(`/api/projects/${project}/expert-drafts/from-job/${encodeURIComponent(id)}`,'POST',{});
  if(!valid())return;
  await refresh();
  if(valid())editContent(r.id);
 }catch(ex){if(valid())toast(ex.message);}
 finally{if(valid()&&button.isConnected)button.disabled=false;}
}

// Starter actions never submit or erase text already entered by the user.
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-action]');if(!b||!canEdit())return;const a=b.dataset.action;
 if(!['expert-starter','expert-revise','expert-revise-cancel'].includes(a))return;
 const d=expertDraft(),input=$('#expert-message');if(!input)return;
 if(a==='expert-starter'){
  if(d.text.trim()||d.revise){toast('已保留你输入的需求；清空后可使用任务起点');input.focus();return;}
  const task=expertGuides[activeExpert].tasks[Number(b.dataset.id)];if(!task)return;
  d.text=task[1];input.value=d.text;
 }
 if(a==='expert-revise'){
  const job=(state.execution||[]).find(j=>j.id===b.dataset.id);
  if(!job||!expertAnswerUsable(job)||job.payload.expert_id!==activeExpert){toast('请选择本专家已完成的有效回复');return;}
  d.revise=job.id;
 }
 if(a==='expert-revise-cancel')d.revise='';
 $('#expert-revision-note').innerHTML=expertRevisionNote();input.focus();
});
