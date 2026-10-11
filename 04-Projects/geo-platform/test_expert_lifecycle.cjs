const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={},nodes=new Map();
const node=k=>{if(!nodes.has(k))nodes.set(k,{innerHTML:'',value:'',textContent:'',disabled:false,addEventListener(){},querySelector:node,classList:{add(){},remove(){}}});return nodes.get(k)};
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector:node,addEventListener(t,f){(listeners[t]??=[]).push(f)},hidden:false},window:{addEventListener(){}},location:{hash:'#skills?expert=content'},localStorage:{getItem(){return null}},setTimeout(){},setInterval(){},clearTimeout(){}});
for(const f of ['app','planning','knowledge','manager','leads','delivery','sample','experts'])vm.runInContext(fs.readFileSync(`static/${f}.js`,'utf8'),ctx);
vm.runInContext(`pid='a';activeExpert='content';me={base_skills:[{id:'faq',name:'选型',version:1}]};state={role:'owner',project:{name:'A'},skill:[],execution:[],connector_status:[]};toast=()=>{};refresh=async()=>{};editContent=()=>{};globalThis.calls=[];api=async(...args)=>{calls.push(args);return {id:'new'}};`,ctx);
const submit=listeners.submit.find(f=>f.toString().includes("e.target.id!=='expert-chat-form'"));assert(submit);
const button={disabled:false,textContent:''},form={id:'expert-chat-form',isConnected:true,querySelector:()=>button};
ctx.fields={get:k=>k==='question'?'继续正常对话':'faq',getAll:()=>[]};
vm.runInContext(`formSubmit=(form,handler)=>{globalThis.pending=handler(fields).catch(e=>{globalThis.failure=e.message});return pending;};`,ctx);
const fire=()=>submit({target:form,preventDefault(){}});
const settle=async()=>{await ctx.pending;await Promise.resolve();await Promise.resolve()};
const job=(workflow,status='running',expert='content')=>({id:'j',job_type:'expert_chat',status,payload:{workflow,expert_id:expert,sources:[],question:'旧问题'},result:{answer:'旧回复'}});
(async()=>{
 for(const flow of ['reference_analysis','repurpose','geo_diagnosis']){
  ctx.jobs=[job(flow)];vm.runInContext('state.execution=jobs;calls=[]',ctx);
  assert(!vm.runInContext('expertBusy()',ctx));assert(!vm.runInContext('expertWorkspace()',ctx).includes('专家处理中…'));
  fire();await settle();assert.equal(ctx.calls.length,1,flow+' should not silently block chat');assert.equal(button.disabled,false);assert.equal(button.textContent,'发送给专家');
 }
 for(const flow of ['chat',undefined]){
  ctx.jobs=[job(flow)];vm.runInContext('state.execution=jobs;calls=[]',ctx);assert(vm.runInContext('expertBusy()',ctx));fire();assert.equal(ctx.calls.length,0);
 }
 ctx.jobs=[job('chat','running','technical')];vm.runInContext('state.execution=jobs;calls=[]',ctx);fire();await settle();assert.equal(ctx.calls.length,1);
 vm.runInContext(`state.execution=[];calls=[];api=(...args)=>{calls.push(args);return new Promise(resolve=>{globalThis.release=resolve})};`,ctx);
 fire();fire();assert.equal(ctx.calls.length,1,'pending HTTP request must block a double send');assert(vm.runInContext('expertBusy()',ctx));ctx.release({id:'new'});await settle();assert(!vm.runInContext('expertBusy()',ctx));
 vm.runInContext(`expertDraft().text='保留未成功需求';api=async()=>{throw Error('网络失败')}`,ctx);fire();await settle();assert.equal(ctx.failure,'网络失败');assert.equal(vm.runInContext('expertDraft().text',ctx),'保留未成功需求');assert(!button.disabled);assert.equal(button.textContent,'发送给专家');
 vm.runInContext(`state.role='viewer';calls=[];api=async(...args)=>{calls.push(args);return {id:'new'}}`,ctx);fire();assert.equal(ctx.calls.length,0);
 for(const [status,discarded,answer] of [['failed',false,'残留回复'],['running',false,'部分回复'],['succeeded',true,'作废回复'],['succeeded',false,'   ']]){
  ctx.jobs=[{...job('chat',status),result:{answer,discarded,reason:'资料已变'}}];vm.runInContext(`state.role='owner';state.execution=jobs;calls=[]`,ctx);
  assert(!vm.runInContext('expertConversation()',ctx).includes('expert-compose'));await vm.runInContext(`saveExpertDraft('j',{disabled:false,isConnected:true})`,ctx);assert.equal(ctx.calls.length,0,'unusable result must not attempt saving');
 }
 ctx.jobs=[job('chat','succeeded')];vm.runInContext(`state.execution=jobs;state.role='owner'`,ctx);assert(vm.runInContext('expertConversation()',ctx).includes('expert-compose'));
 vm.runInContext(`state.role='viewer';calls=[]`,ctx);assert(!vm.runInContext('expertConversation()',ctx).includes('expert-compose'));await vm.runInContext(`saveExpertDraft('j',{disabled:false,isConnected:true})`,ctx);assert.equal(ctx.calls.length,0);
 console.log('PASS: chat/workflow busy consistency, duplicate-send guard, failed-send recovery, role and discarded-result save gates');
})().catch(e=>{console.error(e);process.exitCode=1});
