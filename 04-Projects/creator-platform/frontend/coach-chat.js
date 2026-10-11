const coachStarters={
 'weekly-menu':['帮我安排一周家常菜单和采购清单','今天只有20分钟，怎么搭配一餐？'],
 'chinese-recipe':['帮我改良一道家常菜','我想替换一种食材，怎么做？'],
 'dining-guide':['帮我看看菜单怎么点','外出吃饭，过敏原要怎么确认？'],
 'health-review':['带我复盘这一周的健康习惯','哪些变化值得继续记录？'],
 'supplement-evidence':['这个补剂有哪些人体证据？','服用补剂前需要确认什么？'],
 'rest-and-reflection':['带我做一个短时间放松练习','今天有点累，想整理一下心情'],
 'service-matching':['帮我制定循序渐进的运动计划','力量、步行和平衡练习怎么搭配？'],
 nutrients:['怎样判断一种营养素是否需要补充？','机制研究和人体证据有什么区别？']
};
// Bound the UI wait even if the transport fails to settle. Abort only stops the
// browser request; it does not confirm cancellation of server-side generation.
async function coachRequest(path,body,signal){
 if(signal?.aborted)throw Error('本次等待已取消；服务端可能仍在处理，请重新打开对话核对记录');
 const controller=new AbortController();let timeout;
 let cancel;
 const cancelled=new Promise((_,reject)=>{cancel=()=>{
  reject(Error('本次等待已取消；服务端可能仍在处理，请重新打开对话核对记录'));
  controller.abort();
 }});
 signal?.addEventListener('abort',cancel,{once:true});
 const deadline=new Promise((_,reject)=>{timeout=setTimeout(()=>{
  reject(Error('等待回复已超时，已停止本页等待；服务端可能仍在处理，请稍后再试，勿连续重复提交'));
  controller.abort();
 },270000)});
 try{return await Promise.race([post(path,body,controller.signal),deadline,cancelled])}
 finally{clearTimeout(timeout);signal?.removeEventListener('abort',cancel)}
}
// Local guidance stays outside the replaceable chat log, including while pending.
// This is a user-opened help panel, not symptom detection or medical triage.
function coachUrgentHelp(){return `<details class="coach-urgent-help"><summary>急症求助 · 不要等待聊天回复</summary><div><p><strong>若现在出现突发胸痛、严重呼吸困难、昏厥，或突然说话不清、一侧肢体无力，请立即联系急救。</strong>这些只是部分需要紧急评估的情况。</p><p>在中国大陆可拨打 <a href="tel:120">120 急救</a>；在其他地区请拨打当地急救电话。请身边的人协助，告知所在位置及症状，并遵循接线员指引；不要自行驾车。</p><p>如果你有立即伤害自己或他人的危险，请联系当地急救或警方，并让可信任的人陪伴，尽量远离可能造成伤害的物品。</p><p class="small muted">本页只展示求助指引，不会替你拨号、派出救护车或联系医生。</p></div></details>`}
// Keep earlier user facts verbatim within this modal; never infer a health profile.
function coachPayload(question,history,context=''){
 const recentCount=context?8:10,cutoff=Math.max(0,history.length-recentCount);
 const earlier=history.slice(0,cutoff).filter(h=>h.role==='user').map(h=>h.content);
 if(earlier.length>40||earlier.reduce((size,text)=>size+Array.from(text).length,0)>16000)throw Error('本次对话已达到上下文上限。请重新打开教练，并重新说明本次目标、过敏及用药等限制后继续');
 return {question,earlier_user_messages:earlier,history:[...(context?[{role:'user',content:context.slice(0,4000)}]:[]),...history.slice(cutoff).map(h=>({...h,content:h.content.slice(0,4000)}))]};
}
function openCoach(id,question='',options={}){
 const s=foodSkills.find(s=>s.id===id)||({'qiao':{title:'赛博乔小乔 · 智能助手',desc:'我是小乔。今天过得怎么样？想聊睡眠、吃饭、运动，或者只是说说心情，都可以。'},'nutrients':{title:'营养素咨询',desc:'聊聊营养素的作用、人体证据与风险。'},'general-health':{title:'日常健康助手',desc:'我们从饮食、活动、睡眠或情绪中的一个目标开始。'},'research-learning':{title:'公开研究学习助手',desc:'帮助理解研究，不代表专家本人，未获专家授权。'}})[id];
 if(!s)return;
 const coachContext=options.context||(s.task?`本次咨询主题：${s.title}。用户选择的指导方向：${s.task}。当前对话仅输出文字，没有计时、保存、导出媒体、预约或购买执行工具。可以给可复制的草稿或下一步入口，不得声称已执行这些操作。`:'');
 const endpoint=id==='service-matching'?'general-health':id;
 const history=[];
 const starters=options.starters||coachStarters[id]||[];
 showForm(options.title||s.title,`<p class="small muted">${esc(options.disclosure||'AI 对话 · 问题与本次聊天会交给平台配置的 AI 服务处理。不会自动读取健康档案。无实时文献检索，不替代医疗评估。')}</p>${options.sources?.length?`<details class="research-sources"><summary>本次可参考的研究资料 · ${options.sources.length} 项</summary>${options.sources.map(s=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><br><small>${esc(s.type)}</small></p>`).join('')}</details>`:''}${coachUrgentHelp()}<div class="chat-log" id="coach-log" aria-live="polite"><p>${esc(options.greeting||s.desc)}</p></div>${starters.length?`<div class="coach-starters">${starters.map(q=>`<button type="button" class="secondary" data-coach-starter="${esc(q)}">${esc(q)}</button>`).join('')}</div>`:''}<label>想聊什么？<textarea id="coach-question" maxlength="2000" placeholder="写下想说的话，回车发送，Shift＋回车换行">${esc(question)}</textarea></label><p class="error" id="coach-error" role="alert"></p>`,'发送',()=>{},{local:true});
 const form=document.getElementById('form'),input=document.getElementById('coach-question'),log=document.getElementById('coach-log'),error=document.getElementById('coach-error'),button=document.getElementById('submit');
 const modal=document.getElementById('modal');
 input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();if(!button.disabled)form.requestSubmit()}});
 form.onsubmit=async e=>{
  e.preventDefault();if(button.disabled)return;const q=input.value.trim();if(!q){error.textContent='请输入问题';return}
  button.disabled=true;input.disabled=true;input.value='';button.textContent='等待回复…';error.textContent='';
  log.innerHTML=history.map(chatMessageHtml).join('')+`<p class="chat-question">${esc(q)}</p><p class="small muted" data-coach-wait>正在整理建议，请稍候…</p>`;
  log.scrollTop=log.scrollHeight;
  const slowNotice=setTimeout(()=>{const wait=log.querySelector('[data-coach-wait]');if(wait&&log.isConnected)wait.textContent='连接仍在处理中，这次回复比平时慢，请勿重复发送。';},20000);
  const streamController=new AbortController(),closeStream=()=>streamController.abort();
  modal?.addEventListener('close',closeStream,{once:true});
  modal?.addEventListener('formreplace',closeStream,{once:true});
  try{
   const payload=coachPayload(q,history,coachContext);
   const streamText=text=>{
    if(!log.isConnected||streamController.signal.aborted)return;
    clearTimeout(slowNotice);
    log.innerHTML=history.map(chatMessageHtml).join('')+`<p class="chat-question">${esc(q)}</p><div class="chat-answer" data-coach-stream>${chatAnswer(text)}</div>`;
    log.scrollTop=log.scrollHeight;button.textContent='正在回复…';
   };
   const result=await (typeof coachStreamRequest==='function'
    ?coachStreamRequest('/coaches/'+endpoint+'/chat',payload,streamText,streamController.signal)
    :coachRequest('/coaches/'+endpoint+'/chat',payload,streamController.signal));
   if(payload.earlier_user_messages.length&&result.context_version!==1)throw Error('后台尚未启用长对话信息保留，本次回复未采用。请重新打开教练，并重新说明目标、过敏及用药等限制');
   if(result.answer?.includes('\ufffd'))throw Error('回复显示异常，未采用结果');
   if(!result.answer?.trim())throw Error('未收到有效回复，请重试');
   history.push({role:'user',content:q},{role:'assistant',content:result.answer});
   // The shared modal may have been closed or reopened for another task.
   if(!log.isConnected||streamController.signal.aborted)return;
   log.innerHTML=history.map(chatMessageHtml).join('');log.scrollTop=log.scrollHeight;input.value='';
  }catch(e){if(log.isConnected&&!streamController.signal.aborted){
   // An interrupted/invalid partial answer must not survive as accepted advice.
   log.innerHTML=history.map(chatMessageHtml).join('')+`<p class="chat-question">${esc(q)}</p>`;
   input.value=q;error.textContent=e.message+'；本次回复未采用，问题已保留，可重新发送。';
  }}
  finally{clearTimeout(slowNotice);modal?.removeEventListener?.('close',closeStream);modal?.removeEventListener?.('formreplace',closeStream);if(log.isConnected&&!streamController.signal.aborted){button.disabled=false;input.disabled=false;button.textContent='发送'}}
 };
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-coach]');if(b)openCoach(b.dataset.coach,b.dataset.question||'',b.hasAttribute('data-nutrient-index')&&typeof nutrientConsultOptions==='function'?nutrientConsultOptions(Number(b.dataset.nutrientIndex)):{})});

document.addEventListener('click',e=>{const b=e.target.closest('[data-coach-starter]');if(!b)return;const input=document.getElementById('coach-question');if(input&&!input.disabled){input.value=b.dataset.coachStarter;input.focus()}});
