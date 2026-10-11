function readingSourceUrl(value){
 if(typeof value!=='string')return '';
 try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password?url.href:''}catch{return ''}
}
function readingReferenceHtml(sources){
 if(!sources?.length)return '';
 const original=sources.some(s=>!s.url);
 return `<details><summary>${original?'查看回答时的原文摘录':'查看回答时的参考资料'}</summary>${original?'<p><small>摘录随这条回答保留，不会随重新上传的原文更新。旧回答不代表新版原文的结论。</small></p>':''}${sources.map(s=>`<p><strong>[${esc(s.ref)}] ${esc(s.document||s.location)}</strong><br>${esc(s.text)}<br><small>${esc(s.location)}${s.checked?' · 核对 '+esc(s.checked):''}</small>${readingSourceUrl(s.url)?`<br><a href="${esc(readingSourceUrl(s.url))}" target="_blank" rel="noopener noreferrer">阅读公开来源 ↗</a>`:''}</p>`).join('')}</details>`;
}
function readingAnswer(value){return chatAnswer(value)}
function readingMessageHtml(message){return chatMessageHtml(message)}
// Validate evidence before committing a response to the in-memory conversation.
function readingSources(sources){
 if(sources===undefined)return [];
 if(!Array.isArray(sources)||!sources.every(s=>s&&['ref','location','text'].every(k=>typeof s[k]==='string'&&s[k].trim())&&(s.document===undefined||typeof s.document==='string')&&(s.url===undefined||readingSourceUrl(s.url))))throw Error('引用资料格式不完整，请重新加载核对');
 return sources;
}
function readingMessage(row){
 if(!row||!['user','assistant'].includes(row.role)||typeof row.content!=='string'||!row.content.trim()||row.content.includes('\ufffd')||(row.id!==undefined&&(typeof row.id!=='string'||!row.id))||(row.saved!==undefined&&![true,false,0,1].includes(row.saved)))throw Error('聊天记录格式不完整，请重新加载核对');
 return {...row,saved:!!row.saved,sources:readingSources(row.sources)};
}
function readingHistory(rows){if(!Array.isArray(rows))throw Error('聊天记录格式不完整，请重新加载核对');return rows.map(readingMessage)}
function readingReply(result){
 if(!result||typeof result.answer!=='string'||!result.answer.trim()||result.answer.includes('\ufffd'))throw Error('未收到有效回复，请重新加载核对');
 return readingMessage({role:'assistant',content:result.answer,sources:result.sources,id:result.id});
}
function readingTopicPayload(question,history,context){
 try{return coachPayload(question,history,context)}
 catch(error){throw Error('本次书籍对话已超过安全上下文容量，未继续生成，也未删除历史。请保留问题；若重新打开后仍提示此信息，需要管理员处理历史。')}
}
// Saving is idempotent on the server, but success still requires its receipt.
async function readingSave(book,message){
 const controller=new AbortController();let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{reject(Error('收藏等待超时，结果尚未确认'));controller.abort()},30000)});
 try{
  const result=await Promise.race([post('/books/'+encodeURIComponent(book)+'/save/'+encodeURIComponent(message),{},controller.signal),deadline]);
  if(result?.saved!==true)throw Error('未收到有效的收藏确认');
 }finally{clearTimeout(timer)}
}
function readerNotes(){
 let raw;const entries=[];
 try{
  raw=localStorage.getItem('wld-reading-notes');
  for(let i=0;i<localStorage.length;i++){
   const key=localStorage.key(i);
   if(key?.startsWith('wld-reading-note:')){const value=localStorage.getItem(key);if(value!==null)entries.push([key,value])}
  }
 }catch{throw Error('无法读取本机知识库，已暂停保存；请恢复浏览器存储访问后重试。不要清除原有数据。')}
 try{
  const legacy=raw===null?[]:JSON.parse(raw);
  if(!Array.isArray(legacy))throw Error('Invalid notes');
  const added=entries.map(([key,value])=>{
   const row=JSON.parse(value);
   if(!row||typeof row.id!=='string'||!row.id||key!=='wld-reading-note:'+encodeURIComponent(row.id))throw Error('Invalid note key');
   return row;
  });
  for(const row of [...legacy,...added]){
   if(!row||typeof row!=='object'||Array.isArray(row))throw Error('Invalid note');
   for(const key of ['id','book','source','location','excerpt','note','at','kind','question'])if(row[key]!==undefined&&typeof row[key]!=='string')throw Error('Invalid field');
   if(typeof row.excerpt!=='string'&&typeof row.note!=='string')throw Error('Missing content');
   if(row.sources!==undefined)readingSources(row.sources);
  }
  const legacyIds=new Set(legacy.filter(n=>n.id).map(n=>n.id));
  // New records never rewrite the legacy array. Timestamp ordering is for display only.
  return added.reverse().filter(n=>!legacyIds.has(n.id)).sort((a,b)=>(b.at||'').localeCompare(a.at||'')).concat(legacy);
 }catch{throw Error('本机知识库记录格式异常，已暂停保存；原始数据未修改，请先备份并核对后再继续。')}
}
// All current note writers share this origin-scoped lock, including other tabs.
async function appendReadingNote(note){
 if(typeof navigator==='undefined'||!navigator.locks?.request)throw Error('当前浏览器无法安全协调笔记保存，请保留内容，使用支持 Web Locks 的浏览器并通过本机地址或 HTTPS 打开。');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),5000);
 try{
  await navigator.locks.request('wld-reading-notes-write',{mode:'exclusive',signal:controller.signal},()=>{
   if(controller.signal.aborted)throw Error('笔记保存等待超时');
   // Locks alone cannot make localStorage snapshots transactional across processes.
   // Give every new note its own key so stale list snapshots cannot erase another note.
   if(typeof note.id!=='string'||!note.id)throw Error('笔记缺少编号，未保存');
   const notes=readerNotes();
   if(!notes.some(n=>n.id===note.id))travelSave('wld-reading-note:'+encodeURIComponent(note.id),note);
  });
 }catch(error){
  if(controller.signal.aborted)throw Error('其他页面仍在保存笔记，本次等待超时且未写入。请保留内容，稍后再试。');
  throw error;
 }finally{clearTimeout(timer)}
}
async function saveReadingLocal(book,row,question){
 if(row.role!=='assistant'||row.id||!row.content?.trim())throw Error('此回复不能作为本地交流记录保存');
 const sources=readingSources(row.sources);
 const noteId=row.localNoteId||(row.localNoteId=crypto.randomUUID());
 await appendReadingNote({id:noteId,book:book.id,source:book.title,kind:'ai-public-discussion',question:question||'',excerpt:row.content,note:'',sources,at:new Date().toISOString()});
 row.localSaved=true;
}
function openBookNotes(id){const b=houBooks.find(x=>x.id===id);if(!b)return;const notes=readerNotes().filter(n=>n.book===id);showForm('阅读工作台 · '+b.title,`<p class="notice">阅读记录可直接使用；AI 原文问答尚未接通，也未导入图书全文。以下是平台阅读方法，不是本书摘要。</p><details><summary class="text-button">七天阅读安排</summary><ol><li>确认作者、版本与目录，写下阅读目标。</li><li>选择最关心的一章，记录关键词。</li><li>摘录一个观点，标明页码。</li><li>找出支撑观点的证据和研究对象。</li><li>列出局限、争议与不适用情况。</li><li>写下自己的理解与待核对问题。</li><li>回顾笔记，选择下一章。</li></ol></details>${id==='new-noma'?'<p class="small muted">发酵实践需遵循可靠原配方的盐度、温度、时间和卫生要求；不要凭 AI 推测配方，也不要以试吃判断未知发酵物是否安全。</p>':''}<label>章节 / 页码<input name="location" required maxlength="120" placeholder="如：第 2 章，第 35 页"></label><label>摘录（可留空）<textarea name="excerpt" maxlength="3000" placeholder="粘贴你希望记录的一小段原文"></textarea></label><label>我的理解或问题<textarea name="note" required maxlength="2000"></textarea></label><p class="small muted">仅保存在当前浏览器，不会发送给第三方。</p><details><summary class="text-button">已保存 ${notes.length} 条笔记</summary>${notes.map(n=>`<article class="care-entry"><strong>${esc(n.location)}</strong><p style="white-space:pre-wrap">${esc(n.excerpt)}</p><p style="white-space:pre-wrap">${esc(n.note)}</p></article>`).join('')||'<p>还没有笔记。</p>'}</details>`,'保存阅读笔记',f=>{const location=String(f.get('location')).trim(),note=String(f.get('note')).trim();if(!location||!note)throw Error('请填写章节位置与笔记');return appendReadingNote({id:crypto.randomUUID(),book:id,location,note,excerpt:String(f.get('excerpt')).trim(),at:new Date().toISOString()})},{local:true,message:'阅读笔记已保存到本机'})}
document.addEventListener('click',e=>{const b=e.target.closest('[data-book-reader]');if(b)openReadingChat(b.dataset.bookReader)});
// Bound read-only startup requests separately from slow model generation.
async function readingLoad(path,signal){
 if(signal?.aborted)throw Error('本次资料读取已取消');
 const controller=new AbortController();let timeout;
 let cancel;
 const cancelled=new Promise((_,reject)=>{cancel=()=>{reject(Error('本次资料读取已取消'));controller.abort()}});
 signal?.addEventListener('abort',cancel,{once:true});
 const deadline=new Promise((_,reject)=>{timeout=setTimeout(()=>{reject(Error('读取超时，请点击“重新加载”重试；已输入的问题会保留'));controller.abort()},15000)});
 try{return await Promise.race([api(path,{signal:controller.signal}),deadline,cancelled])}finally{clearTimeout(timeout);signal?.removeEventListener('abort',cancel)}
}
// Timeout covers both upload transport and response parsing. It cannot cancel
// server-side indexing or prove whether a source replacement was committed.
async function readingUpload(id,file,signal){
 if(signal?.aborted)throw Error('上传等待已取消；服务端可能仍在处理，请重新打开核对资料状态');
 const controller=new AbortController();let timeout;
 let cancel;
 const cancelled=new Promise((_,reject)=>{cancel=()=>{reject(Error('上传等待已取消；服务端可能仍在处理，请重新打开核对资料状态'));controller.abort()}});
 signal?.addEventListener('abort',cancel,{once:true});
 const deadline=new Promise((_,reject)=>{timeout=setTimeout(()=>{reject(Error('上传等待已超时，已停止本页等待；服务端可能仍在处理'));controller.abort()},120000)});
 const request=(async()=>{
  const data=new FormData();data.append('file',file);
  const response=await fetch('/api/books/'+id+'/source',{method:'POST',body:data,signal:controller.signal});
  if(controller.signal.aborted)throw Error('上传等待已结束');
  let result;try{result=await response.json()}catch{throw Error('未能读取上传结果')}
  if(controller.signal.aborted)throw Error('上传等待已结束');
  if(!response.ok)throw Error(requestErrorMessage(result,response.status));
  if(result.ready!==true||!Number.isInteger(result.chunks)||result.chunks<1)throw Error('上传返回结果不完整');
  return result;
 })();
 try{return await Promise.race([request,deadline,cancelled])}finally{clearTimeout(timeout);signal?.removeEventListener('abort',cancel)}
}
function readingWelcome(book){
 const guide=typeof readingGuide==='function'?readingGuide(book):{heading:`一起聊聊《${book.title}》`,intro:'从你感兴趣的问题开始，也可以粘贴摘录一起读。',questions:['这本书的底层知识框架与第一性原理是什么？','这本书最牛的观点是什么？','这本书最差的地方在哪里？']};
 return `<div class="reading-welcome"><span class="eyebrow">${esc(book.category||'阅读交流')}</span><h2>${esc(guide.heading)}</h2><p>${esc(guide.intro)}</p><div class="reading-starters">${guide.questions.map(q=>`<button type="button" data-reading-prompt="${esc(q)}">${esc(q)}</button>`).join('')}</div></div>`;
}
async function openReadingChat(id){
 const book=houBooks.find(x=>x.id===id);if(!book)return;
 let history=[],busy=false,sourceReady=false,historyLoaded=false;
 showForm('提问交流 · '+book.title,`<p id="reading-status" class="small muted" hidden>正在检查原文与历史记录…</p><button type="button" id="reading-reload" class="secondary" hidden>重新加载</button><details class="reading-sources"><summary class="text-button">＋ 上传资料 / 管理原文</summary><p class="small muted">支持文字版 PDF、UTF-8 TXT / MD，限 10 MB；仅上传有权使用的资料。文件在本机解析，新上传会替换该书资料。关闭窗口只停止本页等待，后台可能继续解析；重新上传前请先核对当前资料。</p><input type="file" id="reading-file" accept=".pdf,.txt,.md"><button type="button" class="secondary" id="reading-upload">上传并建立原文索引</button><p id="reading-upload-status" class="small muted" role="status"></p></details><div id="reading-log" class="chat-log" aria-live="polite"></div><div class="reading-composer"><label class="reading-question-label">你的问题<textarea rows="2" id="reading-question" maxlength="2000" placeholder="例如：这一章的核心观点是什么？依据在哪里？"></textarea></label><button type="button" class="primary full" id="reading-send">发送问题</button><p id="reading-error" class="error" role="alert"></p></div>`,'关闭',()=>{},{local:true});document.getElementById('submit').hidden=true;const readingModal=document.getElementById('modal');
 const resetReadingLayout=()=>{readingModal.classList.remove('reading-fullscreen');readingModal.removeEventListener?.('close',resetReadingLayout);readingModal.removeEventListener?.('formreplace',resetReadingLayout)};
 readingModal.classList.add('reading-fullscreen');readingModal.addEventListener('close',resetReadingLayout,{once:true});readingModal.addEventListener('formreplace',resetReadingLayout,{once:true});
 const log=document.getElementById('reading-log'),status=document.getElementById('reading-status'),error=document.getElementById('reading-error');
 const send=document.getElementById('reading-send'),question=document.getElementById('reading-question'),upload=document.getElementById('reading-upload'),fileInput=document.getElementById('reading-file');
 const reload=document.getElementById('reading-reload'),uploadStatus=document.getElementById('reading-upload-status');
 const active=()=>log.isConnected&&document.getElementById('modal').open;
 const saving=new Set();
 send.disabled=true;
 function paint(){if(!active())return;log.innerHTML=history.length?history.map((h,i)=>`${readingMessageHtml(h)}${h.role==='assistant'?(h.id?`<button type="button" class="text-button" data-reading-save="${esc(h.id)}">${h.saved?'♥ 已存入长寿日志':'♡ 收藏到长寿日志'}</button>`:`<button type="button" class="text-button" data-reading-local="${i}" ${h.localSaved?'disabled':''}>${h.localSaved?'♥ 已记入本机知识库':'♡ 记入长寿知识库 · 仅当前浏览器'}</button>`):''}${readingReferenceHtml(h.sources)}`).join(''):readingWelcome(book);log.scrollTop=log.scrollHeight}paint();
 async function check(signal){try{const s=await readingLoad('/books/'+id,signal);if(!active()||signal?.aborted)return false;sourceReady=!!s.ready;status.hidden=!s.ready&&!!s.model_ready;status.textContent=s.ready?`已索引：${s.name} · ${s.chunks} 个片段${s.model_ready?'':' · 模型未配置'}`:'可以直接提问 · 当前为主题交流，尚未读取本书全文；可粘贴摘录或上传原文。';send.disabled=!s.model_ready;reload.hidden=true;return true}catch(e){if(active()&&!signal?.aborted){status.hidden=false;status.textContent='原文状态加载失败：'+e.message;send.disabled=true;reload.hidden=false}return false}}
 async function load(){
  if(busy||!active())return;busy=true;reload.disabled=true;send.disabled=true;upload.disabled=true;error.textContent='';status.hidden=true;status.textContent='正在检查原文与历史记录…';let loaded=false;
  const controller=new AbortController(),cancelLoad=()=>controller.abort();
  readingModal.addEventListener('close',cancelLoad,{once:true});
  readingModal.addEventListener('formreplace',cancelLoad,{once:true});
  try{
   if(!historyLoaded){const rows=await readingLoad('/books/'+id+'/history',controller.signal);if(!active()||controller.signal.aborted)return;history=readingHistory(rows);historyLoaded=true;paint()}
   loaded=await check(controller.signal);
  }catch(e){if(active()&&!controller.signal.aborted){status.hidden=false;status.textContent='历史记录加载失败：'+e.message;reload.hidden=false}}
  finally{readingModal.removeEventListener?.('close',cancelLoad);readingModal.removeEventListener?.('formreplace',cancelLoad);busy=false;if(active()&&!controller.signal.aborted){reload.disabled=false;upload.disabled=!loaded}}
 }
 reload.onclick=load;
 upload.onclick=async()=>{
  if(busy||upload.disabled||!active())return;
  const file=fileInput.files[0];
  if(!file){error.textContent='请先选择文件';return}
  if(!/\.(pdf|txt|md)$/i.test(file.name||'')){error.textContent='支持文字版 PDF、UTF-8 TXT / MD';return}
  if(!file.size){error.textContent='文件为空，请选择有内容的资料';return}
  if(file.size>10*1024*1024){error.textContent='文件限 10 MB';return}
  const controller=new AbortController(),cancelUpload=()=>controller.abort();
  readingModal.addEventListener('close',cancelUpload,{once:true});
  readingModal.addEventListener('formreplace',cancelUpload,{once:true});
  busy=true;error.textContent='';upload.disabled=true;fileInput.disabled=true;send.disabled=true;reload.disabled=true;
  uploadStatus.textContent='正在上传并建立原文索引…';status.textContent='正在解析并建立索引…';let loaded=false;
  try{
   const result=await readingUpload(id,file,controller.signal);if(!active()||controller.signal.aborted)return;
   uploadStatus.textContent=`服务端已确认建立索引：${result.chunks} 个片段。正在核对当前资料状态…`;
   loaded=await check(controller.signal);if(!active()||controller.signal.aborted)return;
   uploadStatus.textContent=loaded?'上传已完成，请核对上方当前资料名称。':'上传已获服务端确认，但当前资料状态读取失败；请点击“重新加载”核对。';
  }catch(e){if(active()&&!controller.signal.aborted){
   uploadStatus.textContent=e.message+'。未确认本次上传完成；请先点击“重新加载”核对当前资料名称，勿连续重复上传。读取到旧资料也不代表后台已停止处理。';
   status.hidden=false;status.textContent='请核对上传后的原文状态';reload.hidden=false;send.disabled=true;
  }}finally{readingModal.removeEventListener?.('close',cancelUpload);readingModal.removeEventListener?.('formreplace',cancelUpload);busy=false;if(active()&&!controller.signal.aborted){fileInput.disabled=false;reload.disabled=false;upload.disabled=!loaded}}
 };
 send.onclick=async(options={})=>{
  if(busy||send.disabled||!active())return;
  const q=question.value.trim();if(!q){error.textContent='请填写问题';return}
  busy=true;error.textContent='';send.disabled=true;question.disabled=true;question.value='';send.textContent='等待回复…';
  paint();if(!history.length)log.innerHTML='';
  log.innerHTML+=`<p class="chat-question" style="white-space:pre-wrap">${esc(q)}</p><div class="reading-wait" role="status"><span class="reading-wait-dots" aria-hidden="true"><i></i><i></i><i></i></span><div><strong>问题已提交，正在等待回复</strong><span data-reading-elapsed>已等待 0 秒</span><small>回复将在收到后显示，可继续阅读上面的内容。</small></div></div>`;
  log.scrollTop=log.scrollHeight;
  const started=Date.now();let progressTimer;
  const streamController=new AbortController(),modal=document.getElementById('modal'),closeStream=()=>streamController.abort();
  modal.addEventListener('close',closeStream,{once:true});
  modal.addEventListener('formreplace',closeStream,{once:true});
  const updateProgress=()=>{
   if(!active())return;
   const seconds=Math.floor((Date.now()-started)/1000),elapsed=log.querySelector?.('[data-reading-elapsed]');
   if(elapsed)elapsed.textContent=`已等待 ${seconds} 秒${seconds>=20?' · 本次回复较慢，请勿重复发送':''}`;
   progressTimer=setTimeout(updateProgress,1000);
  };
  try{
   const context={role:'user',content:JSON.stringify({book:book.title,editorialTopic:typeof readingGuide==='function'?readingGuide(book).intro:'',author:typeof bookMetadata!=='undefined'?bookMetadata[id]?.author:'未核实',...(options.quick?{answerFormat:'这次推荐问题先用120—180字回答：直接给核心结论和3个简短要点，关键词用Markdown粗体标记，分段表达，不用列表短横线，不写开场白、不重复总结。保留必要的证据局限与安全提示；未核验原文不得编造本书观点。用户追问细节再展开。'}:{}),mode:'书籍主题交流：未提供全文，不得声称读过本书、编造章节页码或把通用知识当原书观点。不确定作者版本或内容时明确说明，可请用户粘贴摘录。'},null,0)};
   const streamText=text=>{
    if(!active()||streamController.signal.aborted)return;
    clearTimeout(progressTimer);
    log.querySelector('.reading-wait')?.remove();
    let reply=log.querySelector('[data-reading-stream]');
    if(!reply){reply=document.createElement('div');reply.setAttribute('data-reading-stream','');log.appendChild(reply)}
    reply.innerHTML=readingAnswer(text);send.textContent='正在回复…';log.scrollTop=log.scrollHeight;
   };
   const topicRequest=typeof coachStreamRequest==='function'?(path,body)=>coachStreamRequest(path,body,streamText,streamController.signal):(path,body)=>coachRequest(path,body,streamController.signal);
   const request=sourceReady?coachRequest('/books/'+id+'/chat',{question:q,history:[]},streamController.signal):topicRequest('/coaches/research-learning/chat',{book_id:id,...readingTopicPayload(q,history,context.content)});
   progressTimer=setTimeout(updateProgress,1000);
   const result=await request;if(!active()||streamController.signal.aborted)return;
   if(!sourceReady&&history.length>8&&result.context_version!==1)throw Error('后台尚未启用早期对话保留，本次回复未采用。请保留问题，待后台更新后继续');
   const reply=readingReply(result);history.push({role:'user',content:q},reply);paint();
  }catch(e){if(active()&&!streamController.signal.aborted){
   paint();question.value=q;
   error.textContent=e.message+'；问题已恢复到输入框。'+(sourceReady?'若连接中断或超时，请重新打开本书查看历史，确认没有收到回复后再重试。':'');
  }}finally{clearTimeout(progressTimer);modal.removeEventListener?.('close',closeStream);modal.removeEventListener?.('formreplace',closeStream);busy=false;if(active()&&!streamController.signal.aborted){question.disabled=false;send.disabled=false;send.textContent='发送问题'}}
 };
 question.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();send.onclick()}});
 log.addEventListener('click',e=>{
  const starter=e.target.closest('[data-reading-prompt]');
  if(!starter||busy||send.disabled||!active())return;
  question.value=starter.dataset.readingPrompt;
  send.onclick({quick:true});
 });
 log.addEventListener('click',async e=>{
  const local=e.target.closest('[data-reading-local]');
  if(local){
   if(!active()||local.disabled)return;
   if(busy){error.textContent='请等本次回复完成后再记录。';return}
   const index=Number(local.dataset.readingLocal),row=history[index];
   if(!Number.isInteger(index)||!row||row.id||row.localSaved)return;
   const localLabel=local.textContent;local.disabled=true;local.textContent='正在保存…';error.textContent='';
   try{
    await saveReadingLocal(book,row,history[index-1]?.role==='user'?history[index-1].content:'');
    if(active()){
     if(!busy)paint();
     else if(local.isConnected){local.textContent='♥ 已记入本机知识库';local.disabled=true}
     toast('已记入「我的 → 知识库」，仅保存在当前浏览器。');
    }
   }catch(e){if(active()){error.textContent=e.message+'；尚未确认保存，请保留本次回复。';if(local.isConnected){local.disabled=false;local.textContent=localLabel}}}
   return;
  }
  const b=e.target.closest('[data-reading-save]');if(!b||!active())return;
  const messageId=b.dataset.readingSave,row=history.find(h=>h.role==='assistant'&&h.id===messageId);
  if(!row||row.saved||saving.has(messageId))return;
  if(busy){error.textContent='请等本次回复完成后再收藏。';return}
  saving.add(messageId);b.disabled=true;error.textContent='';
  try{
   await readingSave(id,messageId);if(!active())return;
   row.saved=true;
   // A new answer may have started while saving; never repaint its partial text.
   if(!busy)paint();
   else if(b.isConnected){b.textContent='♥ 已存入长寿日志';b.disabled=true}
   toast('已收藏，可在「我的 → 知识库」查看');
  }catch(e){if(active()){error.textContent=e.message+'。请重新打开本书或刷新知识库核对，未确认前不显示已收藏。';if(b.isConnected)b.disabled=false}}
  finally{saving.delete(messageId)}
 });
 await load();
}
function openBookInsights(id, excerpt='', source=''){
 const book=houBooks.find(b=>b.id===id);
 showForm(book?'记录知识点 · '+book.title:'记录知识点',`<p>把读到的好观点留下来，也可以写下自己的理解。</p><label>原文摘录<textarea name="excerpt" rows="6" maxlength="6000" placeholder="在这里粘贴你复制的关键内容">${esc(excerpt)}</textarea></label><label>来源书籍 / 文章<input name="source" maxlength="300" value="${esc(book?.title||source)}" placeholder="书名、文章标题或链接"></label><label>章节 / 页码（选填）<input name="location" maxlength="120"></label><label>我的理解（选填）<textarea name="note" maxlength="2000"></textarea></label><p class="small muted">保存到当前浏览器的长寿知识库，不会发送给 AI。</p>`,'保存到我的长寿知识库',f=>{
 const excerpt=String(f.get('excerpt')||'').trim(),note=String(f.get('note')||'').trim();
 if(!excerpt&&!note)throw Error('请粘贴摘录或写下你的理解');
 return appendReadingNote({id:crypto.randomUUID(),book:book?.id||'',source:String(f.get('source')||'').trim(),location:String(f.get('location')||'').trim(),excerpt,note,at:new Date().toISOString()});
 },{local:true,message:'已保存到我的长寿知识库'});
}
function readingBackupSnapshot(){
 // Preserve exact values, including damaged JSON, and never include unrelated storage.
 const capture=()=>{
  const keys=new Set(['wld-reading-notes']);
  for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key?.startsWith('wld-reading-note:'))keys.add(key)}
  return [...keys].sort().flatMap(key=>{const value=localStorage.getItem(key);return value===null?[]:[{key,value}]});
 };
 let first,second;
 try{first=capture();second=capture()}catch{throw Error('无法读取本机笔记，未创建备份文件。请恢复浏览器存储访问后重试，勿清除原数据。')}
 if(JSON.stringify(first)!==JSON.stringify(second))throw Error('笔记正在变化，未创建备份文件。请暂停其他页面的保存后重试。');
 return {format:'wld-local-reading-backup',version:1,exported_at:new Date().toISOString(),scope:'browser-local-reading-notes-only',entries:second};
}
function downloadReadingBackup(){
 const snapshot=readingBackupSnapshot();
 if(!snapshot.entries.length)throw Error('当前浏览器没有可导出的本机笔记。');
 const blob=new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json;charset=utf-8'});
 let url,link;
 try{
  url=URL.createObjectURL(blob);link=document.createElement('a');link.href=url;
  link.download='wld-reading-notes-'+snapshot.exported_at.replace(/[:.]/g,'-')+'.json';
  link.hidden=true;document.body.appendChild(link);link.click();
 }catch{if(url)URL.revokeObjectURL(url);throw Error('未能发起备份下载，请检查浏览器下载权限后重试。')}
 finally{link?.remove()}
 setTimeout(()=>URL.revokeObjectURL(url),60000);
 return '已发起下载，请在浏览器下载列表核对 JSON 文件。导出不代表记录已修复。';
}
function readingBackupControl(){return `<button type="button" class="secondary" data-knowledge-export>导出本机笔记</button><p class="small muted">仅导出当前浏览器的摘录与交流笔记，不含服务端收藏或上传原文。文件未加密，可能含个人信息，请妥善保管。导出前请暂停其他页面的保存；暂不支持自动导入恢复。</p><p class="small" data-knowledge-export-status role="status" aria-live="polite"></p>`}
function personalKnowledgeNotes(){
 let notes;try{notes=readerNotes()}catch(error){return `<section class="portal-section"><h2>我的摘录与笔记</h2><p class="error" role="alert">${esc(error.message)}</p><p>无法确认笔记是否为空。修复读取前请勿清除浏览器数据。</p>${readingBackupControl()}</section>`}
 return `<section class="portal-section"><h2>我的摘录与笔记</h2><button class="primary" data-knowledge-add>记录知识点</button>${readingBackupControl()}${notes.map(n=>`<article class="card"><span class="chip">${esc(n.source||houBooks.find(b=>b.id===n.book)?.title||'个人笔记')}</span><p class="small muted">${esc(n.location||'')} · ${esc((n.at||'').slice(0,10))}</p>${n.kind==='ai-public-discussion'?`<p class="small muted">AI 公开资料交流 · 非原书摘录 · 未经专业复核</p>${n.question?`<p><strong>我的问题</strong> ${esc(n.question)}</p>`:''}${chatAnswer(n.excerpt||'')}${readingReferenceHtml(n.sources||[])}`:`<p style="white-space:pre-wrap">${esc(n.excerpt||'')}</p>`}${n.note?`<h3>我的理解</h3><p style="white-space:pre-wrap">${esc(n.note)}</p>`:''}</article>`).join('')||'<p>从文章或书中复制一段有价值的内容，粘贴到这里保存。</p>'}</section>`}
let selectedKnowledge=null;
document.addEventListener('selectionchange',()=>{
 const selection=window.getSelection();const text=selection?.toString().trim();const node=selection?.anchorNode;
 const element=node?.nodeType===1?node:node?.parentElement;
 const existing=document.getElementById('save-selection-knowledge');
 if(!text||text.length>6000||!element?.closest('#app')||element.closest('input,textarea')){selectedKnowledge=null;existing?.remove();return}
 selectedKnowledge={text,source:(document.querySelector('#app h1')?.textContent||document.title)+' · '+location.href};
 if(!existing){const button=document.createElement('button');button.id='save-selection-knowledge';button.type='button';button.className='primary';button.textContent='记入长寿知识库';button.style.cssText='position:fixed;bottom:100px;left:50%;transform:translateX(-50%);z-index:80';button.onpointerdown=e=>e.preventDefault();button.onclick=()=>{const value=selectedKnowledge;button.remove();if(value)openBookInsights('',value.text,value.source)};document.body.appendChild(button)}
});
document.addEventListener('click',e=>{if(e.target.closest('[data-knowledge-add]'))openBookInsights('')});
document.addEventListener('click',e=>{const b=e.target.closest('[data-book-insights]');if(b)openBookInsights(b.dataset.bookInsights)});


document.addEventListener('click',e=>{
 const button=e.target.closest('[data-knowledge-export]');if(!button||button.disabled)return;
 const status=button.closest('section')?.querySelector('[data-knowledge-export-status]');
 button.disabled=true;
 try{const message=downloadReadingBackup();if(status)status.textContent=message}
 catch(error){if(status)status.textContent=error.message}
 finally{button.disabled=false}
});
