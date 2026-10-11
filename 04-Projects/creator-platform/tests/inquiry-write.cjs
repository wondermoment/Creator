// Real form/controller code with synthetic HTTP, clocks and records only.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const app=fs.readFileSync('frontend/app.js','utf8'),formCode=app.slice(app.indexOf('let formGeneration='),app.indexOf('\nfunction record()'));
function setup(){
 const nodes={},requests=[],timers=new Map(),toasts=[];let serial=0;
 for(const id of ['modal','form','submit','form-error','modal-title','fields'])nodes[id]={};
 nodes.modal.showModal=function(){this.open=true};nodes.modal.close=function(){this.open=false};
 const c={AbortController,crypto:{randomUUID:()=> 'synthetic-request-key'},document:{addEventListener(){}},window:{addEventListener(){}},state:{overview:{},page:'account'},esc:String,date:String,render(){},reload:async()=>{},toast:m=>toasts.push(m),$:selector=>nodes[selector.slice(1)],FormData:class{constructor(target){return new Map(Object.entries(target))}},setTimeout:(fn,ms)=>{const id=++serial;timers.set(id,{fn,ms});return id},clearTimeout:id=>timers.delete(id),api:(path,options={})=>options.method?new Promise((resolve,reject)=>requests.push({path,options,resolve,reject})):Promise.resolve([])};
 vm.createContext(c);vm.runInContext(formCode,c);vm.runInContext(fs.readFileSync('frontend/customer-service.js','utf8'),c);
 return {c,nodes,requests,timers,toasts,submit:target=>nodes.form.onsubmit({preventDefault(){},target}),tick(){for(const t of [...timers.values()]){assert.equal(t.ms,30000);t.fn()}}};
}
const input={kind:'了解报价与日期',need:'合成需求'};
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};
(async()=>{
 let h=setup();h.c.serviceInquiry('合成项目');let p=h.submit(input);assert(h.nodes.submit.disabled);await h.submit(input);assert.equal(h.requests.length,1);
 h.tick();await p;assert(h.nodes.modal.open);assert(!h.nodes.submit.disabled);assert(h.nodes['form-error'].textContent.includes('服务端可能已处理'));assert(h.requests[0].options.signal.aborted);assert.equal(h.toasts.length,0);assert.equal(h.timers.size,0);
 // Changes after an uncertain POST cannot accidentally reuse the key with different content.
 await h.submit({...input,need:'不同合成内容'});assert.equal(h.requests.length,1);assert(h.nodes['form-error'].textContent.includes('不要修改内容'));
 p=h.submit(input);assert.equal(h.requests.length,2);assert.equal(h.requests[0].options.body,h.requests[1].options.body);
 h.requests[1].resolve({id:'synthetic-id',status:'pending'});await p;assert(!h.nodes.modal.open);assert.equal(h.toasts.length,1);
 h.requests[0].resolve({id:'late',status:'pending'});await flush();assert.equal(h.toasts.length,1);
 // Invalid response, HTTP rejection and empty values never produce success.
 for(const bad of [null,{}, {id:'x'}, {id:'x',status:'unknown'}]){
  h=setup();h.c.serviceInquiry('合成项目');p=h.submit(input);h.requests[0].resolve(bad);await p;assert(h.nodes.modal.open);assert.equal(h.toasts.length,0);assert(h.nodes['form-error'].textContent.includes('未能确认'));
 }
 h=setup();h.c.serviceInquiry('合成项目');await h.submit({...input,need:'   '});assert.equal(h.requests.length,0);assert(h.nodes['form-error'].textContent.includes('请填写'));
 p=h.submit(input);h.requests[0].reject(Error('合成HTTP错误'));await p;assert(h.nodes.modal.open);assert.equal(h.toasts.length,0);
 // PATCH remains blocked in that form after an unknown result; refreshing/reopening is necessary.
 h=setup();vm.runInContext("inquiryRows=[{id:'synthetic-id',subject:'合成项目',status:'pending',timeline:[{}]}];inquiryLoaded=true",h.c);
 h.c.inquiryFollow('synthetic-id');p=h.submit({status:'following',note:'合成跟进'});h.tick();await p;
 assert(h.nodes['form-error'].textContent.includes('刷新'));await h.submit({status:'following',note:'合成跟进'});assert.equal(h.requests.length,1);
 assert.equal(JSON.parse(h.requests[0].options.body).expected_version,1);assert.equal(h.requests[0].options.method,'PATCH');
 // Late success cannot close a replacement modal or toast a false result.
 h.nodes.modal.close();h.c.showForm('新窗口','新内容','新按钮',async()=>{});h.nodes.submit.disabled=true;
 h.requests[0].resolve({ok:true});await flush();assert(h.nodes.modal.open);assert(h.nodes.submit.disabled);assert.equal(h.toasts.length,0);
 // The ordinary confirmed PATCH path still succeeds, trims whitespace and refreshes.
 h=setup();vm.runInContext("inquiryRows=[{id:'synthetic-id',subject:'合成项目',status:'following',timeline:[{},{}]}]",h.c);
 h.c.inquiryFollow('synthetic-id');p=h.submit({status:'closed',note:'  合成完成  '});assert.equal(JSON.parse(h.requests[0].options.body).note,'合成完成');h.requests[0].resolve({ok:true});await p;assert.equal(h.toasts.length,1);assert(!h.nodes.modal.open);
 console.log('PASS: inquiry POST/PATCH bounded wait, ambiguous result warnings, fixed-key exact retry, changed-payload rejection, PATCH no-repeat, response validation, real form recovery and late modal isolation. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
