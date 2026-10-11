// Synthetic DOM harness: no browser, network, or user data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function harness(){
 let nodes={},pending=[],timers=new Map(),sequence=0,markup='';
 const el=()=>({isConnected:true,open:true,disabled:false,value:'',checked:true,files:[],classList:{add(){},remove(){}},events:{},addEventListener(t,f){(this.events[t]||=[]).push(f)},removeEventListener(t,f){this.events[t]=(this.events[t]||[]).filter(x=>x!==f)},innerHTML:'',textContent:''});
 const ctx={AbortController,setTimeout(fn,ms){timers.set(++sequence,{fn,ms});return sequence},clearTimeout:id=>timers.delete(id),houBooks:[{id:'a',title:'A'},{id:'b',title:'B'}],esc:x=>x,toast(){},FormData:class{},document:{getElementById:id=>nodes[id],addEventListener(){}},showForm(title,body){markup=body;for(const n of Object.values(nodes))n.isConnected=false;nodes={};for(const id of ['modal','form','submit','reading-reload','reading-log','reading-status','reading-error','reading-send','reading-question','reading-upload','reading-file','reading-upload-status','insights-body','insights-error'])nodes[id]=el();},api(url,options={}){return new Promise((resolve,reject)=>pending.push({url,signal:options.signal,resolve,reject}))},post(url,body,signal){return new Promise((resolve,reject)=>pending.push({url,body,signal,resolve,reject}))}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),ctx);vm.runInContext(fs.readFileSync('frontend/coach-chat.js','utf8'),ctx);vm.runInContext(fs.readFileSync('frontend/book-reader.js','utf8'),ctx);
 return {ctx,get markup(){return markup},get nodes(){return nodes},pending,timers};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function ready(h,id){const task=h.ctx.openReadingChat(id);h.pending.shift().resolve([]);await tick();h.pending.shift().resolve({ready:true,model_ready:true,name:'synthetic',chunks:1});await task;}
(async()=>{
 // Startup and manual reload must stop waiting on modal close/replacement,
 // even when the transport ignores AbortSignal and resolves much later.
 for(const phase of ['history','status','reload'])for(const action of ['close','formreplace']){
  const t=harness();let loading,request;
  if(phase==='reload'){
   await ready(t,'a');loading=t.nodes['reading-reload'].onclick();request=t.pending.shift();
  }else{
   loading=t.ctx.openReadingChat('a');request=t.pending.shift();
   if(phase==='status'){request.resolve([]);await tick();request=t.pending.shift()}
  }
  const modal=t.nodes.modal,oldStatus=t.nodes['reading-status'],before=oldStatus.textContent;
  if(action==='close')modal.open=false;
  for(const callback of [...modal.events[action]])callback();
  await loading;assert(request.signal.aborted);assert.equal(t.timers.size,0);assert.equal(t.pending.length,0);
  assert.equal(oldStatus.textContent,before);assert.equal(modal.events.close.length,0);assert.equal(modal.events.formreplace.length,0);
  await ready(t,'b');t.nodes['reading-question'].value='new book draft';const newStatus=t.nodes['reading-status'].textContent;
  request.resolve(phase==='history'?[{role:'assistant',content:'late old history'}]:{ready:true,model_ready:true,name:'late old source',chunks:99});await tick();
  assert.equal(t.pending.length,0);assert.equal(t.nodes['reading-question'].value,'new book draft');assert.equal(t.nodes['reading-status'].textContent,newStatus);
  assert(!t.nodes['reading-log'].innerHTML.includes('late old'));assert.equal(t.timers.size,0);
 }
 console.log('PASS: six startup/history/status/manual-reload close/replacement cases cancel transport, settle ignored signals, clean listeners/timers and isolate late results.');
 for(const sourceReady of [false,true]){
  const h=harness(),init=h.ctx.openReadingChat('a');
  const click=()=>h.nodes['reading-log'].events.click.forEach(fn=>fn({target:{closest:selector=>selector==='[data-reading-prompt]'?{dataset:{readingPrompt:'这本书最牛的观点是什么？'}}:null}}));
  click();assert.equal(h.pending.length,1,'Loading must not send a question');
  h.pending.shift().resolve([]);await tick();h.pending.shift().resolve({ready:sourceReady,model_ready:true});await init;
  click();click();assert.equal(h.pending.length,1,'One click sends exactly once; pending duplicate ignored');
  const req=h.pending.shift();assert.equal(req.body.question,'这本书最牛的观点是什么？');
  assert.equal(h.nodes['reading-question'].value,'');assert(h.nodes['reading-log'].innerHTML.includes('问题已提交'));
  if(!sourceReady)assert(JSON.parse(req.body.history[0].content).answerFormat.includes('120—180'));
  req.reject(Error('合成断网'));await tick();
  assert.equal(h.nodes['reading-question'].value,'这本书最牛的观点是什么？');assert.equal(h.nodes['reading-send'].disabled,false);
 }
 const h=harness();await ready(h,'a');assert(!h.markup.includes('coach-urgent-help'));assert(!h.markup.includes('reading-consent'));assert.equal(h.timers.size,0);h.nodes['reading-question'].value='A question';const reply=h.nodes['reading-send'].onclick();const old=h.pending.shift();await ready(h,'b');h.nodes['reading-question'].value='B draft';old.resolve({answer:'A reply',sources:[],id:'x'});await reply;assert.equal(h.nodes['reading-question'].value,'B draft');assert.ok(!h.nodes['reading-log'].innerHTML.includes('A reply'));
 h.nodes['reading-question'].value='retain on error';const failed=h.nodes['reading-send'].onclick();h.pending.shift().reject(Error('offline'));await failed;assert.equal(h.nodes['reading-question'].value,'retain on error');assert.equal(h.nodes['reading-question'].disabled,false);assert.equal(h.nodes['reading-send'].disabled,false);
 const i=harness();const init=i.ctx.openReadingChat('a');i.pending.shift().resolve([]);await tick();i.pending.shift().resolve({ready:false,model_ready:true});await init;assert.equal(i.nodes['reading-send'].disabled,false);i.nodes['reading-question'].value='这本书讲什么';const general=i.nodes['reading-send'].onclick();const request=i.pending.shift();assert.equal(request.url,'/coaches/research-learning/chat');request.resolve({answer:'主题讨论，不是原书摘要'});await general;assert.ok(i.nodes['reading-log'].innerHTML.includes('主题讨论'));assert.equal(i.nodes['reading-question'].value,'');
 for(const sourceReady of [false,true]){
  const t=harness();const init=t.ctx.openReadingChat('a');t.pending.shift().resolve([]);await tick();t.pending.shift().resolve({ready:sourceReady,model_ready:true});await init;
  t.nodes['reading-question'].value='synthetic timeout';assert(!t.markup.includes('reading-consent'));
  const send=t.nodes['reading-send'].onclick();await t.nodes['reading-send'].onclick();assert.equal(t.pending.length,1);
  assert.equal(t.nodes['reading-question'].value,'');assert(t.nodes['reading-log'].innerHTML.includes('synthetic timeout'));
  assert(t.nodes['reading-log'].innerHTML.includes('问题已提交'));assert(t.nodes['reading-log'].innerHTML.includes('已等待 0 秒'));
  assert.equal([...t.timers.values()].filter(x=>x.ms===1000).length,1);
  const req=t.pending.shift();assert.equal(req.url,sourceReady?'/books/a/chat':'/coaches/research-learning/chat');assert.equal(req.body.book_id,sourceReady?undefined:'a');assert(req.signal instanceof AbortSignal);
  assert.equal([...t.timers.values()][0].ms,270000);[...t.timers.values()][0].fn();await send;
  assert(req.signal.aborted);assert.equal(t.nodes['reading-question'].value,'synthetic timeout');assert.equal(t.nodes['reading-send'].disabled,false);assert.equal(t.nodes['reading-question'].disabled,false);assert.equal(t.timers.size,0);
  assert(t.nodes['reading-error'].textContent.includes('服务端可能仍在处理'));assert.equal(t.nodes['reading-error'].textContent.includes('重新打开本书查看历史'),sourceReady);
  t.nodes['reading-question'].value='new draft';req.resolve({answer:'late answer'});await tick();assert.equal(t.nodes['reading-question'].value,'new draft');assert(!t.nodes['reading-log'].innerHTML.includes('late answer'));assert.equal(t.pending.length,0);
  const retry=t.nodes['reading-send'].onclick();const retried=t.pending.shift();assert.equal(retried.body.history.length,sourceReady?0:1);retried.resolve({answer:'retry reply'});await retry;assert(t.nodes['reading-log'].innerHTML.includes('retry reply'));assert.equal(t.timers.size,0);
 }
 // Startup history/status timeout, manual recovery and late-result isolation.
 for(const phase of ['history','status']){
  const t=harness();const init=t.ctx.openReadingChat('a');
  assert(!t.markup.includes('coach-urgent-help'));
  if(phase==='status'){t.pending.shift().resolve([{role:'assistant',content:'saved history'}]);await tick()}
  const stalled=t.pending.shift();assert(stalled.signal instanceof AbortSignal);
  t.nodes['reading-question'].value='keep this draft';
  assert.equal([...t.timers.values()][0].ms,15000);[...t.timers.values()][0].fn();await init;
  assert(stalled.signal.aborted);assert.equal(t.timers.size,0);assert(t.nodes['reading-send'].disabled);assert.equal(t.nodes['reading-reload'].hidden,false);assert.equal(t.nodes['reading-reload'].disabled,false);assert(t.nodes['reading-status'].textContent.includes('读取超时'));assert.equal(t.pending.length,0);
  const retry=t.nodes['reading-reload'].onclick();await t.nodes['reading-reload'].onclick();assert.equal(t.pending.length,1);
  if(phase==='history'){t.pending.shift().resolve([]);await tick()}
  t.pending.shift().resolve({ready:false,model_ready:true});await retry;
  assert.equal(t.nodes['reading-reload'].hidden,true);assert.equal(t.nodes['reading-send'].disabled,false);assert.equal(t.nodes['reading-upload'].disabled,false);assert.equal(t.nodes['reading-question'].value,'keep this draft');
  stalled.resolve(phase==='history'?[{role:'assistant',content:'stale history'}]:{ready:true,model_ready:false});await tick();
  assert(!t.nodes['reading-log'].innerHTML.includes('stale history'));assert.equal(t.nodes['reading-send'].disabled,false);assert.equal(t.timers.size,0);
  if(phase==='status')assert(t.nodes['reading-log'].innerHTML.includes('saved history'));
 }
 for(const phase of ['history','status']){
  const t=harness();const init=t.ctx.openReadingChat('a');if(phase==='status'){t.pending.shift().resolve([]);await tick()}
  t.pending.shift().reject(Error('synthetic offline'));await init;assert.equal(t.nodes['reading-reload'].hidden,false);assert(t.nodes['reading-send'].disabled);assert.equal(t.timers.size,0);assert.equal(t.pending.length,0);
 }
 const unavailable=harness();const unavailableInit=unavailable.ctx.openReadingChat('a');unavailable.pending.shift().resolve([]);await tick();unavailable.pending.shift().resolve({ready:true,model_ready:false,name:'test',chunks:1});await unavailableInit;assert(unavailable.nodes['reading-send'].disabled);assert(unavailable.nodes['reading-status'].textContent.includes('模型未配置'));assert.equal(unavailable.timers.size,0);
 const switched=harness();const oldLoad=switched.ctx.openReadingChat('a');const oldRead=switched.pending.shift();await ready(switched,'b');const before=switched.nodes['reading-status'].textContent;oldRead.resolve([]);await oldLoad;assert.equal(switched.nodes['reading-status'].textContent,before);assert.equal(switched.pending.length,0);assert.equal(switched.timers.size,0);
 // Malformed evidence must fail before committing a turn, so retry remains usable.
 for(const mode of [false,true]){
  for(const result of [null,{answer:12},{answer:'bad evidence',sources:{}},{answer:'bad evidence',sources:[null]},{answer:'bad evidence',sources:[{ref:'S1',location:'page'}]},{answer:'bad evidence',sources:[],id:{}}]){
   const t=harness();const init=t.ctx.openReadingChat('a');t.pending.shift().resolve([{role:'assistant',content:'prior valid answer',sources:[],saved:1,id:'stored-id'}]);await tick();t.pending.shift().resolve({ready:mode,model_ready:true});await init;
   t.nodes['reading-question'].value='retained evidence question';const bad=t.nodes['reading-send'].onclick();t.pending.shift().resolve(result);await bad;
   assert.equal(t.nodes['reading-question'].value,'retained evidence question');assert(!t.nodes['reading-send'].disabled);assert(t.nodes['reading-error'].textContent.includes('问题已恢复到输入框'));assert(!t.nodes['reading-log'].innerHTML.includes('bad evidence'));assert(t.nodes['reading-log'].innerHTML.includes('prior valid answer'));
   const retry=t.nodes['reading-send'].onclick(),req=t.pending.shift();if(!mode){assert.equal(req.body.history.length,2);assert(!JSON.stringify(req.body.history).includes('bad evidence'))}
   req.resolve({answer:'valid recovered answer',sources:[{ref:'S1',location:'合成页码',text:'合成摘录',document:'合成资料'}],id:'new-id'});await retry;
   assert(t.nodes['reading-log'].innerHTML.includes('valid recovered answer'));assert(t.nodes['reading-log'].innerHTML.includes('合成摘录'));assert.equal(t.nodes['reading-question'].value,'');assert.equal(t.timers.size,0);
  }
 }
 for(const rows of [null,{},[null],[{role:'system',content:'unexpected'}],[{role:'assistant',content:1}],[{role:'assistant',content:'text',sources:'invalid'}],[{role:'assistant',content:'text',saved:2}]]){
  const t=harness(),init=t.ctx.openReadingChat('a');t.pending.shift().resolve(rows);await init;
  assert(t.nodes['reading-send'].disabled);assert.equal(t.nodes['reading-reload'].hidden,false);assert.equal(t.pending.length,0);
  const retry=t.nodes['reading-reload'].onclick();t.pending.shift().resolve([{role:'assistant',content:'valid history',sources:[],saved:0}]);await tick();t.pending.shift().resolve({ready:false,model_ready:true});await retry;
  assert(!t.nodes['reading-send'].disabled);assert(t.nodes['reading-log'].innerHTML.includes('valid history'));assert.equal(t.timers.size,0);
 }
 const closedStream=harness();let bookSignal;
 closedStream.ctx.coachStreamRequest=(path,body,onText,signal)=>{bookSignal=signal;return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('closed')),{once:true}))};
 const closedInit=closedStream.ctx.openReadingChat('a');closedStream.pending.shift().resolve([]);await tick();closedStream.pending.shift().resolve({ready:false,model_ready:true});await closedInit;
 closedStream.nodes['reading-question'].value='关闭问题';const closedSend=closedStream.nodes['reading-send'].onclick();
 closedStream.nodes.modal.open=false;closedStream.nodes.modal.events.close.forEach(f=>f());await closedSend;
 assert(bookSignal.aborted);assert.equal(closedStream.timers.size,0);assert.equal(closedStream.nodes.modal.events.close.length,0);
 console.log('PASS: malformed answers/evidence never enter history; both reading routes preserve draft/prior turns and recover; malformed initial history reloads; SQLite saved 0/1 accepted.');
 const long=harness(),longInit=long.ctx.openReadingChat('a');long.pending.shift().resolve([]);await tick();long.pending.shift().resolve({ready:false,model_ready:true});await longInit;
 for(let i=0;i<6;i++){
  long.nodes['reading-question'].value=i===0?'严重花生过敏，目前服用华法林':'后续阅读问题'+i;
  const task=long.nodes['reading-send'].onclick(),req=long.pending.shift();
  req.resolve({answer:'合成完整回答',context_version:1});await task;
 }
 long.nodes['reading-question'].value='现在能用这个建议吗';
 const guarded=long.nodes['reading-send'].onclick(),oldBackend=long.pending.shift();
 assert.equal(oldBackend.body.earlier_user_messages[0],'严重花生过敏，目前服用华法林');
 assert.equal(oldBackend.body.book_id,'a');assert.equal(oldBackend.body.history.length,9);
 oldBackend.resolve({answer:'旧后台遗漏限制的回复'});await guarded;
 assert(!long.nodes['reading-log'].innerHTML.includes('旧后台遗漏限制的回复'));
 assert.equal(long.nodes['reading-question'].value,'现在能用这个建议吗');
 assert(long.nodes['reading-error'].textContent.includes('早期对话保留'));
 const retryLong=long.nodes['reading-send'].onclick(),newBackend=long.pending.shift();
 assert.deepEqual(newBackend.body,oldBackend.body);newBackend.resolve({answer:'保留限制后的回答',context_version:1});await retryLong;
 assert(long.nodes['reading-log'].innerHTML.includes('保留限制后的回答'));
 assert.throws(()=>long.ctx.readingTopicPayload('继续',Array.from({length:100},()=>({role:'user',content:'历史'})),'书籍'),/未删除历史/);
 console.log('PASS: public-book long conversations retain early user restrictions; old backend answer rejected, same payload retry and capacity limit explicit.');
 for(const mode of ['success','invalid','timeout','stale','during-reply']){
  const saved=harness(),init=saved.ctx.openReadingChat('a');
  saved.pending.shift().resolve([{role:'assistant',content:'可收藏的合成回答',sources:[],id:'save-id',saved:0}]);await tick();saved.pending.shift().resolve({ready:false,model_ready:true});await init;
  const button={dataset:{readingSave:'save-id'},disabled:false,isConnected:true};
  const handler=saved.nodes['reading-log'].events.click[1];
  const event={target:{closest:s=>s==='[data-reading-save]'?button:null}};
  const first=handler(event);await handler(event);assert.equal(saved.pending.length,1,'Deduplicate repeated save events');
  const saveRequest=saved.pending.shift();
  if(mode==='stale'){
   await ready(saved,'b');saved.nodes['reading-question'].value='另一书草稿';saveRequest.reject(Error('旧收藏失败'));await first;
   assert.equal(saved.nodes['reading-error'].textContent,'');assert.equal(saved.nodes['reading-question'].value,'另一书草稿');
  }else if(mode==='during-reply'){
   saved.nodes['reading-question'].value='新问题';const next=saved.nodes['reading-send'].onclick(),reply=saved.pending.shift();
   const partial=saved.nodes['reading-log'].innerHTML;
   saveRequest.resolve({saved:true});await first;assert.equal(saved.nodes['reading-log'].innerHTML,partial,'Save must not repaint a pending reply');
   reply.resolve({answer:'新完整回答',context_version:1});await next;assert(saved.nodes['reading-log'].innerHTML.includes('已存入'));
  }else{
   if(mode==='timeout'){
    const deadline=[...saved.timers.values()].find(t=>t.ms===30000);assert(deadline);deadline.fn();await first;
    assert(saveRequest.signal.aborted);saveRequest.resolve({saved:true});await tick();
   }else{saveRequest.resolve(mode==='success'?{saved:true}:{saved:false});await first}
   assert.equal(saved.nodes['reading-log'].innerHTML.includes('♥ 已存入'),mode==='success');
   if(mode!=='success'){assert.equal(button.disabled,false);assert(saved.nodes['reading-error'].textContent.includes('核对'))}
  }
  assert.equal(saved.timers.size,0);
 }
 console.log('PASS: save receipt validation, duplicate suppression, timeout/late receipt, cross-book errors and in-flight answer preservation.');
 const local=harness(),localInit=local.ctx.openReadingChat('a');local.pending.shift().resolve([]);await tick();local.pending.shift().resolve({ready:false,model_ready:true});await localInit;
 local.nodes['reading-question'].value='公开资料问题';const ask=local.nodes['reading-send'].onclick();
 assert(!local.nodes['reading-log'].innerHTML.includes('data-reading-local'));
 local.pending.shift().resolve({answer:'完整公开资料回答',sources:[],context_version:1});await ask;
 assert(local.nodes['reading-log'].innerHTML.includes('data-reading-local="1"'));
 let captured=0;local.ctx.saveReadingLocal=(book,row,q)=>{assert.equal(book.id,'a');assert.equal(q,'公开资料问题');captured++;row.localSaved=true};
 const localButton={dataset:{readingLocal:'1'},disabled:false};
 const localHandler=local.nodes['reading-log'].events.click[1],localEvent={target:{closest:s=>s==='[data-reading-local]'?localButton:null}};
 await localHandler(localEvent);await localHandler(localEvent);assert.equal(captured,1);assert.equal(local.pending.length,0);
 assert(local.nodes['reading-log'].innerHTML.includes('已记入本机知识库'));
 console.log('PASS: complete public answer exposes local knowledge action; carries original question and does not send server save requests.');
 for(const mode of ['failure','new-answer','other-book']){
  const t=harness(),start=t.ctx.openReadingChat('a');t.pending.shift().resolve([]);await tick();t.pending.shift().resolve({ready:false,model_ready:true});await start;
  t.nodes['reading-question'].value='local save test';const asking=t.nodes['reading-send'].onclick();t.pending.shift().resolve({answer:'completed public reply',sources:[]});await asking;
  let resolveSave,rejectSave;
  t.ctx.saveReadingLocal=(book,row)=>new Promise((resolve,reject)=>{resolveSave=()=>{row.localSaved=true;resolve()};rejectSave=reject});
  const button={dataset:{readingLocal:'1'},disabled:false,isConnected:true,textContent:'保存'};
  const event={target:{closest:s=>s==='[data-reading-local]'?button:null}};
  const saving=t.nodes['reading-log'].events.click[1](event);
  assert(button.disabled);assert.equal(button.textContent,'正在保存…');
  if(mode==='failure'){
   rejectSave(Error('synthetic lock timeout'));await saving;assert(!button.disabled);assert.equal(button.textContent,'保存');assert(t.nodes['reading-error'].textContent.includes('尚未确认'));
  }else if(mode==='other-book'){
   await ready(t,'b');t.nodes['reading-question'].value='new book draft';const html=t.nodes['reading-log'].innerHTML;resolveSave();await saving;
   assert.equal(t.nodes['reading-log'].innerHTML,html);assert.equal(t.nodes['reading-question'].value,'new book draft');
  }else{
   t.nodes['reading-question'].value='next question';const next=t.nodes['reading-send'].onclick();const html=t.nodes['reading-log'].innerHTML;
   resolveSave();await saving;assert.equal(t.nodes['reading-log'].innerHTML,html);assert(button.textContent.includes('已记入'));
   t.pending.shift().resolve({answer:'next answer',sources:[]});await next;
  }
 }
 console.log('PASS: asynchronous local saves show pending state, restore on failure, and preserve another book or an in-flight reply.');
 console.log('PASS: startup GET timeouts/manual retry/draft preservation/late and cross-book isolation; clean book header without consent/urgent panels.');
 console.log('PASS: both reading routes have bounded wait, direct-send/duplicate guards, draft recovery, no automatic retry, late-answer isolation and source-history reminder; existing routes pass. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
