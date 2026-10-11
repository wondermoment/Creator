// Synthetic DOM, files, network and virtual timers. Never uploads to a server.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){
 let nodes={},markup='',sequence=0;const timers=new Map(),reads=[],uploads=[],models=[];
 const element=()=>({isConnected:true,open:true,disabled:false,value:'',files:[],checked:true,hidden:false,innerHTML:'',textContent:'',classList:{add(){},remove(){}},events:{},addEventListener(type,fn){(this.events[type]??=[]).push(fn)},removeEventListener(type,fn){this.events[type]=(this.events[type]||[]).filter(f=>f!==fn)},fire(type){for(const fn of [...(this.events[type]||[])])fn()}});
 const c={AbortController,houBooks:[{id:'a',title:'Synthetic A'},{id:'b',title:'Synthetic B'}],esc:String,toast(){},requestErrorMessage:r=>r.detail,
  FormData:class{constructor(){this.rows=[]}append(...row){this.rows.push(row)}},
  document:{addEventListener(){},getElementById:id=>nodes[id]},
  setTimeout(fn,ms){timers.set(++sequence,{fn,ms});return sequence},clearTimeout:id=>timers.delete(id),
  showForm(title,body){nodes.modal?.fire('formreplace');markup=body;for(const node of Object.values(nodes))node.isConnected=false;nodes={};for(const id of ['modal','submit','reading-log','reading-status','reading-error','reading-send','reading-question','reading-upload','reading-file','reading-reload','reading-upload-status'])nodes[id]=element()},
  api(url,options){return new Promise((resolve,reject)=>reads.push({url,options,resolve,reject}))},
  fetch(url,options){return new Promise((resolve,reject)=>uploads.push({url,options,resolve,reject}))},
  post(...args){models.push(args);throw Error('unexpected model request')}
 };vm.createContext(c);
 for(const file of ['coach-chat','book-reader'])vm.runInContext(fs.readFileSync('frontend/'+file+'.js','utf8'),c);
 return {c,reads,uploads,models,timers,get nodes(){return nodes},get markup(){return markup}};
}
async function ready(h,id='a'){
 const p=h.c.openReadingChat(id);h.reads.shift().resolve([]);await tick();h.reads.shift().resolve({ready:false,model_ready:true});await p;
 h.nodes['reading-file'].files=[{name:'synthetic.txt',size:100}];h.nodes['reading-question'].value='synthetic draft';
}
const response=(data,ok=true)=>({ok,status:ok?200:422,json:async()=>data});
async function reload(h){const p=h.nodes['reading-reload'].onclick();assert.equal(h.reads.length,1);h.reads.shift().resolve({ready:true,model_ready:true,name:'current.txt',chunks:2});await p;}
(async()=>{
 const invalid=harness();await ready(invalid);
 for(const file of [null,{name:'x.exe',size:10},{name:'x.txt',size:0},{name:'x.pdf',size:10*1024*1024+1}]){
  invalid.nodes['reading-file'].files=file?[file]:[];await invalid.nodes['reading-upload'].onclick();assert(invalid.nodes['reading-error'].textContent);assert.equal(invalid.uploads.length,0);assert.equal(invalid.timers.size,0);
 }
 const success=harness();await ready(success);const p=success.nodes['reading-upload'].onclick();
 assert(success.nodes['reading-send'].disabled);assert(success.nodes['reading-file'].disabled);assert(success.nodes['reading-upload'].disabled);
 await success.nodes['reading-upload'].onclick();await success.nodes['reading-send'].onclick();await success.nodes['reading-reload'].onclick();assert.equal(success.uploads.length,1);assert.equal(success.reads.length,0);assert.equal(success.models.length,0);
 const req=success.uploads.shift();assert.equal(req.url,'/api/books/a/source');assert.equal(req.options.method,'POST');assert(req.options.signal instanceof AbortSignal);assert.equal(req.options.body.rows[0][0],'file');assert.equal(req.options.body.rows[0][1].name,'synthetic.txt');
 req.resolve(response({ready:true,chunks:3}));await tick();assert(success.nodes['reading-upload-status'].textContent.includes('服务端已确认'));assert.equal(success.timers.size,1);
 success.reads.shift().resolve({ready:true,model_ready:true,name:'synthetic.txt',chunks:3});await p;
 assert.equal(success.nodes['reading-question'].value,'synthetic draft');assert.equal(success.nodes['reading-file'].files[0].name,'synthetic.txt');assert(!success.nodes['reading-file'].disabled);assert(!success.nodes['reading-send'].disabled);assert(!success.nodes['reading-upload'].disabled);assert.equal(success.timers.size,0);
 success.nodes.modal.fire('close');assert(!req.options.signal.aborted,'completed upload listener must be removed');
 for(const failure of ['transport-timeout','body-timeout','offline','http','invalid-json','invalid-success']){
  const h=harness();await ready(h);const p=h.nodes['reading-upload'].onclick();const req=h.uploads.shift();let resolveBody;
  if(failure==='body-timeout'){req.resolve({ok:true,json:()=>new Promise(resolve=>resolveBody=resolve)});await tick()}
  if(failure.endsWith('timeout')){assert.equal([...h.timers.values()][0].ms,120000);[...h.timers.values()][0].fn()}
  else if(failure==='offline')req.reject(Error('synthetic offline'));
  else if(failure==='http')req.resolve(response({detail:'没有提取到文字'},false));
  else if(failure==='invalid-json')req.resolve({ok:true,json:async()=>{throw Error('invalid JSON')}});
  else req.resolve(response({ready:true,chunks:0}));
  await p;assert.equal(h.timers.size,0);assert.equal(h.uploads.length,0);assert.equal(h.reads.length,0,'no automatic status/retry requests');assert.equal(h.models.length,0);
  assert(h.nodes['reading-upload-status'].textContent.includes('未确认本次上传完成'));assert(h.nodes['reading-upload-status'].textContent.includes('旧资料也不代表后台已停止'));assert.equal(h.nodes['reading-reload'].hidden,false);assert(!h.nodes['reading-reload'].disabled);assert(h.nodes['reading-send'].disabled);assert(h.nodes['reading-upload'].disabled);assert(!h.nodes['reading-file'].disabled);assert.equal(h.nodes['reading-question'].value,'synthetic draft');
  if(failure.endsWith('timeout'))assert(req.options.signal.aborted);
  const warning=h.nodes['reading-upload-status'].textContent;await reload(h);assert(!h.nodes['reading-send'].disabled);assert(!h.nodes['reading-upload'].disabled);assert.equal(h.nodes['reading-upload-status'].textContent,warning,'status refresh must not erase uncertainty');
  req.resolve(response({ready:true,chunks:99}));resolveBody?.({ready:true,chunks:99});await tick();assert.equal(h.reads.length,0);assert.equal(h.nodes['reading-upload-status'].textContent,warning);assert.equal(h.nodes['reading-question'].value,'synthetic draft');
 }
 const statusFailure=harness();await ready(statusFailure);const partial=statusFailure.nodes['reading-upload'].onclick();statusFailure.uploads.shift().resolve(response({ready:true,chunks:2}));await tick();statusFailure.reads.shift().reject(Error('status offline'));await partial;
 assert(statusFailure.nodes['reading-upload-status'].textContent.includes('已获服务端确认'));assert(statusFailure.nodes['reading-send'].disabled);assert(statusFailure.nodes['reading-upload'].disabled);await reload(statusFailure);assert(!statusFailure.nodes['reading-send'].disabled);
 for(const outcome of ['success','error']){
  const h=harness();await ready(h);const p=h.nodes['reading-upload'].onclick();const stale=h.uploads.shift();await ready(h,'b');h.nodes['reading-question'].value='B draft';const before=h.nodes['reading-status'].textContent;
  outcome==='success'?stale.resolve(response({ready:true,chunks:9})):stale.reject(Error('old upload failed'));await p;
  assert.equal(h.nodes['reading-question'].value,'B draft');assert.equal(h.nodes['reading-status'].textContent,before);assert.equal(h.nodes['reading-upload-status'].textContent,'');assert.equal(h.reads.length,0);assert.equal(h.timers.size,0);
 }
 for(const phase of ['transport','body','status'])for(const action of ['close','formreplace']){
  const h=harness();await ready(h);const modal=h.nodes.modal;
  const task=h.nodes['reading-upload'].onclick(),request=h.uploads.shift();let finishBody,statusRead;
  if(phase==='body'){request.resolve({ok:true,json:()=>new Promise(resolve=>finishBody=resolve)});await tick()}
  if(phase==='status'){request.resolve(response({ready:true,chunks:2}));await tick();statusRead=h.reads.shift()}
  const previousStatus=h.nodes['reading-upload-status'].textContent;
  if(action==='close'){modal.open=false;modal.fire('close')}else modal.fire('formreplace');
  await task;assert.equal(h.timers.size,0);assert.equal(h.nodes['reading-upload-status'].textContent,previousStatus);
  assert((phase==='status'?statusRead.options.signal:request.options.signal).aborted);
  assert.equal(modal.events.close.length,0);assert.equal(modal.events.formreplace.length,0);
  await ready(h,'b');const before=h.nodes['reading-status'].textContent;h.nodes['reading-question'].value='retained new draft';
  let parsedLate=false;
  request.resolve({ok:true,json:async()=>{parsedLate=true;return {ready:true,chunks:99}}});finishBody?.({ready:true,chunks:99});statusRead?.resolve({ready:true,model_ready:true,name:'old-late.txt',chunks:99});await tick();
  assert(!parsedLate);assert.equal(h.nodes['reading-status'].textContent,before);assert.equal(h.nodes['reading-question'].value,'retained new draft');assert.equal(h.reads.length,0);assert.equal(h.timers.size,0);
 }
 const pre=harness(),cancelled=new AbortController();cancelled.abort();
 await assert.rejects(pre.c.readingUpload('a',{name:'test.txt',size:1},cancelled.signal),/已取消/);
 await assert.rejects(pre.c.readingLoad('/books/a',cancelled.signal),/已取消/);
 assert.equal(pre.uploads.length,0);assert.equal(pre.reads.length,0);assert.equal(pre.timers.size,0);
 console.log('PASS: upload/body/status cancellation on close/replacement settles uncooperative transport, removes listeners/timers, ignores late results, preserves new window; pre-cancel sends nothing.');
 console.log('PASS: upload validation, bounded transport/body parsing, duplicate/send guards, confirmed vs uncertain outcomes, manual status recovery, persistent warning, draft/file preservation and cross-book isolation. No real network, model, files or data changed.');
})().catch(e=>{console.error(e);process.exit(1)});
