// Actual showForm + coach/book UI, synthetic DOM/stream; no user records.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function harness(mode='stream'){
 const nodes={},timers=new Map(),pending=[];let serial=0,children=[];
 function node(){const e=new EventTarget();Object.assign(e,{isConnected:true,value:'',textContent:'',innerHTML:'',disabled:false,files:[],querySelector(){return null}});const classes=new Set();e.classList={add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)};return e}
 for(const id of ['modal','form','fields','submit','form-error','modal-title'])nodes[id]=node();
 nodes.modal.open=false;nodes.modal.showModal=()=>{nodes.modal.open=true};nodes.modal.close=()=>{nodes.modal.open=false;nodes.modal.dispatchEvent(new Event('close'))};
 Object.defineProperty(nodes.fields,'innerHTML',{set(html){for(const id of children){nodes[id].isConnected=false;delete nodes[id]}children=[];for(const m of html.matchAll(/\bid="([^"]+)"/g)){nodes[m[1]]=node();children.push(m[1])}}});
 const c={Event,AbortController,URL,FormData:class{},foodSkills:[],houBooks:[{id:'a',title:'合成书A'},{id:'b',title:'合成书B'}],esc:String,
  $:s=>nodes[s.slice(1)],document:{addEventListener(){},getElementById:id=>nodes[id]},toast(){},render(){},reload:async()=>{},
  setTimeout(fn){timers.set(++serial,fn);return serial},clearTimeout:id=>timers.delete(id),
  api:async path=>path.endsWith('/history')?[]:{ready:mode==='source',model_ready:true},
  coachStreamRequest(path,body,onText,signal){return new Promise((resolve,reject)=>{signal.addEventListener('abort',()=>reject(Error('cancelled')),{once:true});pending.push({path,body,onText,signal,resolve,reject})})}
 };
 if(mode!=='stream'){
  delete c.coachStreamRequest;
  // Deliberately ignores signal, proving cancellation settles independently.
  c.post=(path,body,signal)=>new Promise((resolve,reject)=>pending.push({path,body,signal,resolve,reject,onText(){}}));
 }
 vm.createContext(c);const app=fs.readFileSync('frontend/app.js','utf8');vm.runInContext(app.slice(app.indexOf('let formGeneration='),app.indexOf('\nfunction record()')),c);
 for(const f of ['chat-format','coach-chat','book-reader'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
 return {c,nodes,pending,timers};
}
(async()=>{
 for(const mode of ['stream','source','fallback'])for(const from of ['coach','book'])for(const to of ['coach','book','form','close']){
  const h=harness(mode);
  if(from==='book')await h.c.openReadingChat('a');else h.c.openCoach('general-health');
  const input=h.nodes[from==='book'?'reading-question':'coach-question'];input.value='旧窗口合成问题';
  const old=from==='book'?h.nodes['reading-send'].onclick():h.nodes.form.onsubmit({preventDefault(){}});
  const request=h.pending.shift();assert(!request.signal.aborted);
  if(to==='book')await h.c.openReadingChat('b');else if(to==='coach')h.c.openCoach('qiao');else if(to==='close')h.nodes.modal.close();else h.c.showForm('普通表单','<input id="new-draft">','保存',()=>{});
  assert(request.signal.aborted,`${from}->${to}: replacing the modal must cancel its previous stream`);
  await old;assert.equal(h.timers.size,0);
  if(to==='close')h.c.showForm('新表单','<input id="new-draft">','保存',()=>{});
  const draft=h.nodes[to==='book'?'reading-question':to==='coach'?'coach-question':'new-draft'];draft.value='新草稿';
  request.onText('旧流迟到内容');request.resolve({answer:'迟到回复',sources:[]});await Promise.resolve();assert.equal(draft.value,'新草稿');
  const log=h.nodes[to==='book'?'reading-log':'coach-log'];if(log)assert(!log.innerHTML.includes('迟到'));
  assert.equal(h.nodes.modal.classList.contains('reading-fullscreen'),to==='book');
  if(to==='book'||to==='coach'){
   const next=to==='book'?h.nodes['reading-send'].onclick():h.nodes.form.onsubmit({preventDefault(){}}),nextRequest=h.pending.shift();
   assert(!nextRequest.signal.aborted,'Old cleanup must not abort the new request');
   nextRequest.resolve({answer:'新窗口完整答复',sources:[],context_version:1});await next;
   assert(log.innerHTML.includes('新窗口完整答复'));assert.equal(h.timers.size,0);
  }
  h.nodes.modal.close();assert(!h.nodes.modal.classList.contains('reading-fullscreen'));
 }
 console.log('PASS: 24 stream/source/fallback coach/book replacement and close scenarios abort transport, settle uncooperative requests, block late content, preserve new drafts/replies and clean timers/layout. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
