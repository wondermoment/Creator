from pathlib import Path
p=Path(__file__).resolve().parents[1]/'frontend/book-reader.js'
s=p.read_text('utf-8');start=s.index(' send.onclick=async()=>');end=s.index(" question.addEventListener('keydown'",start)
s=s[:start]+''' send.onclick=async()=>{
  if(busy||send.disabled||!active())return;
  const q=question.value.trim();if(!q){error.textContent='请填写问题';return}
  busy=true;error.textContent='';send.disabled=true;question.disabled=true;question.value='';send.textContent='等待回复…';
  paint();if(!history.length)log.innerHTML='';
  log.innerHTML+=`<p class="chat-question" style="white-space:pre-wrap">${esc(q)}</p><div class="reading-wait" role="status"><span class="reading-wait-dots" aria-hidden="true"><i></i><i></i><i></i></span><div><strong>问题已提交，正在等待回复</strong><span data-reading-elapsed>已等待 0 秒</span><small>回复将在收到后显示，可继续阅读上面的内容。</small></div></div>`;
  log.scrollTop=log.scrollHeight;
  const started=Date.now();let progressTimer;
  const updateProgress=()=>{
   if(!active())return;
   const seconds=Math.floor((Date.now()-started)/1000),elapsed=log.querySelector?.('[data-reading-elapsed]');
   if(elapsed)elapsed.textContent=`已等待 ${seconds} 秒${seconds>=20?' · 本次回复较慢，请勿重复发送':''}`;
   progressTimer=setTimeout(updateProgress,1000);
  };
  try{
   const context={role:'user',content:JSON.stringify({book:book.title,editorialTopic:typeof readingGuide==='function'?readingGuide(book).intro:'',author:typeof bookMetadata!=='undefined'?bookMetadata[id]?.author:'未核实',mode:'书籍主题交流：未提供全文，不得声称读过本书、编造章节页码或把通用知识当原书观点。不确定作者版本或内容时明确说明，可请用户粘贴摘录。'},null,0)};
   const request=sourceReady?coachRequest('/books/'+id+'/chat',{question:q,history:[]}):coachRequest('/coaches/research-learning/chat',{question:q,history:[context,...history.slice(-8).map(h=>({role:h.role,content:h.content.slice(0,4000)}))]});
   progressTimer=setTimeout(updateProgress,1000);
   const result=await request;if(!active())return;
   const reply=readingReply(result);history.push({role:'user',content:q},reply);paint();
  }catch(e){if(active()){
   paint();question.value=q;
   error.textContent=e.message+'；问题已恢复到输入框。'+(sourceReady?'若连接中断或超时，请重新打开本书查看历史，确认没有收到回复后再重试。':'');
  }}finally{clearTimeout(progressTimer);busy=false;if(active()){question.disabled=false;send.disabled=false;send.textContent='发送问题'}}
 };
'''+s[end:];p.write_text(s,encoding='utf-8')
p=p.parent/'index.html';s=p.read_text('utf-8').replace('book-reader.js?v=formatted-14','book-reader.js?v=progress-15').replace('sunny-theme.css?v=reading-format-20261006','sunny-theme.css?v=reading-progress-20261006');p.write_text(s,encoding='utf-8')
p=p.parents[1]/'tests/book-reader-async.cjs';s=p.read_text('utf-8').replace("includes('问题已保留')","includes('问题已恢复到输入框')");p.write_text(s,encoding='utf-8')
