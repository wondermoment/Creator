const fs=require('fs'),vm=require('vm'),assert=require('assert');
const button={disabled:false},form={dataset:{job:'one'},querySelector:()=>button,isConnected:true,reset(){this.resetCalled=true}};
let feedback='更简洁',calls=[],lost=true;
const ctx=vm.createContext({console,Map,Set,JSON,crypto:require('crypto').webcrypto,FormData:class{get(){return feedback}},
 document:{addEventListener(){}},pid:'p',state:{content:[],execution:[{id:'one',status:'succeeded',payload:{workflow:'repurpose',core_topic:'测试选题',repurpose_channel:'moments',question:'采购建议'},result:{answer:'旧结果'}}]},
 page:()=> 'repurpose',$:()=>null,canEdit:()=>true,refresh:async()=>{},toast:()=>{},form,
 api:async(url,method,body)=>{calls.push(body);if(lost){lost=false;throw Error('lost response')}return{id:'new'}}});
vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),ctx);
vm.runInContext('refresh=async()=>{}',ctx);
(async()=>{
 await vm.runInContext('submitRepurposeRewrite(form)',ctx);
 assert.equal(calls.length,1);assert(!form.resetCalled);assert(!button.disabled);
 await vm.runInContext('submitRepurposeRewrite(form)',ctx);
 assert.equal(calls.length,2);assert.equal(calls[0].request_key,calls[1].request_key);
 assert.equal(calls[1].rewrite_job_id,'one');assert.equal(calls[1].repurpose_channel,'moments');assert.equal(calls[1].core_topic,'测试选题');assert.equal(calls[1].rewrite_feedback,'更简洁');
 assert.equal(ctx.state.execution[0].result.answer,'旧结果');assert(form.resetCalled);
 feedback='';await vm.runInContext('submitRepurposeRewrite(form)',ctx);assert.equal(calls.length,2);
 feedback='第一次修改';form.resetCalled=false;
 let finish;ctx.api=async()=>new Promise(r=>finish=r);
 vm.runInContext("repurposeFeedback.set(repurposeEditKey('one'),'第一次修改')",ctx);
 const pending=vm.runInContext('submitRepurposeRewrite(form)',ctx);
 feedback='补充：保留标题';vm.runInContext("repurposeFeedback.set(repurposeEditKey('one'),'补充：保留标题')",ctx);
 finish({id:'another'});await pending;
 assert.equal(vm.runInContext("repurposeFeedback.get(repurposeEditKey('one'))",ctx),'补充：保留标题','late success must retain newer feedback');
 assert(!form.resetCalled,'newer user input must not be reset');assert(!button.disabled);
 ctx.epoch=1;form.resetCalled=false;feedback='新会话意见';
 const stale=vm.runInContext('submitRepurposeRewrite(form)',ctx);
 ctx.epoch=2;vm.runInContext("clearRepurposeSession();repurposeFeedback.set(repurposeEditKey('one'),'重新登录后的输入');repurposeRewriting.add(repurposeEditKey('one'))",ctx);
 finish({id:'old-session'});await stale;
 assert(!form.resetCalled,'old login session must not reset same-user new session');
 assert.equal(vm.runInContext("repurposeFeedback.get(repurposeEditKey('one'))",ctx),'重新登录后的输入');
 assert(vm.runInContext("repurposeRewriting.has(repurposeEditKey('one'))",ctx),'old cleanup must preserve new session in-flight state');
 console.log('PASS: single-output rewrite, lost-response key reuse, retained original, feedback and topic, empty-feedback guard');
})().catch(e=>{console.error(e);process.exitCode=1});
