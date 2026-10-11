const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/commerce.js','utf8'),app=fs.readFileSync('frontend/app.js','utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const snapshot=()=>({mode:'sandbox',live_payment:false,products:[{id:'oats',name:'合成燕麦',price:100,stock:4}],agents:[],orders:[],ledger:[],transfers:[],audit:[]});
function setup(){
 const requests=[],timers=new Map(),nodes={};let n=0,toasts=0;
 for(const id of ['modal','form','submit','form-error','modal-title','fields'])nodes['#'+id]={};
 nodes['#modal'].showModal=function(){this.open=true};nodes['#modal'].close=function(){this.open=false};
 const fields=new Map([['quantity','1'],['referral',''],['name','合成代理'],['parent','']]);
 const ctx={AbortController,URLSearchParams,esc:String,date:String,location:{search:'',hash:'#shop'},crypto:{randomUUID:()=> 'request-fixed'},state:{page:'commerce'},render(){},managedCatalog:()=>'',inquiryAdmin:()=>'',toast(){toasts++},window:{addEventListener(){}},document:{addEventListener(){}},$:s=>nodes[s],FormData:class{constructor(){return fields}},setTimeout(fn){timers.set(++n,fn);return n},clearTimeout(id){timers.delete(id)},api(path,opts){const d=deferred();requests.push({...d,path,opts});return d.promise}};
 vm.createContext(ctx);vm.runInContext(source,ctx);vm.runInContext(app.slice(app.indexOf('let formGeneration='),app.indexOf('\nfunction record()')),ctx);
 ctx.seed=snapshot();vm.runInContext('commerceData=seed',ctx);
 return {ctx,requests,timers,nodes,fields,get toasts(){return toasts},submit:()=>nodes['#form'].onsubmit({preventDefault(){},target:{}}),expire(){for(const fn of [...timers.values()])fn()}};
}
const orderReply=body=>({id:'a'.repeat(32),request_key:body.request_key,product_id:body.product_id,quantity:body.quantity,agent1:body.referral,total:100,status:'pending'});
(async()=>{
 const h=setup();const opening=h.ctx.commerceBuy('oats');h.requests[0].resolve(snapshot());await opening;
 const pending=h.submit();const first=JSON.parse(h.requests[1].opts.body);h.expire();await pending;
 assert.equal(h.nodes['#modal'].open,true);assert.equal(h.nodes['#submit'].disabled,false);assert.match(h.nodes['#form-error'].textContent,/30秒/);assert.equal(h.requests[1].opts.signal.aborted,true);assert.equal(h.timers.size,0);assert.equal(h.ctx.commerceReady(),false);
 h.fields.set('quantity','2');await h.submit();assert.equal(h.requests.length,2);assert.match(h.nodes['#form-error'].textContent,/勿修改/);
 h.requests[1].resolve(orderReply(first));await Promise.resolve();assert.equal(h.toasts,0);
 h.fields.set('quantity','1');const retry=h.submit();assert.deepEqual(JSON.parse(h.requests[2].opts.body),first);h.requests[2].resolve(orderReply(first));await retry;
 assert.equal(h.nodes['#modal'].open,false);assert.equal(h.toasts,1);assert.equal(h.requests[3].path,'/commerce/snapshot');h.expire();await new Promise(r=>setImmediate(r));assert.equal(h.timers.size,0);
 const agent=setup();agent.ctx.commerceAgentForm();const creating=agent.submit();agent.requests[0].reject(Error('connection lost'));await creating;await agent.submit();assert.equal(agent.requests.length,1);assert.equal(agent.nodes['#modal'].open,true);
 const action=setup();const updating=action.ctx.commerceOrderAction('order-one','cancel');await assert.rejects(action.ctx.commerceWrite('/other',{},()=>true),/仍在等待/);action.requests[0].resolve({mode:'sandbox',status:'paid'});await assert.rejects(updating,/结果不完整/);await assert.rejects(action.ctx.commerceOrderAction('order-one','refund'),/刷新/);assert.equal(action.requests.length,1);assert.equal(action.timers.size,0);
 const race=setup();const oldRead=race.ctx.commerceLoad();const write=race.ctx.commerceWrite('/synthetic',{},r=>r?.ok===true);assert.equal(await oldRead,null);race.requests[0].resolve(snapshot());race.requests[1].resolve({ok:true});await write;assert.equal(race.ctx.commerceReady(),false);assert.equal(race.timers.size,0);
 const good=setup();const paid=good.ctx.commerceOrderAction('order-one','simulate-pay');good.requests[0].resolve({mode:'sandbox',status:'settled',idempotent:true});await paid;assert.equal(good.requests[1].path,'/commerce/snapshot');good.expire();await new Promise(r=>setImmediate(r));assert.equal(good.timers.size,0);
 for(const reply of [null,{}, {id:'wrong'}, {mode:'live',status:'cancelled'}]){const bad=setup();const job=bad.ctx.commerceOrderAction('o','cancel');bad.requests[0].resolve(reply);await assert.rejects(job,/未能确认/);assert.equal(bad.timers.size,0)}
 console.log('PASS: real form timeout recovery, same-key immutable order retry, duplicate agent guard, receipt validation, single write, stale read invalidation, and confirmed completion before refresh');
})().catch(e=>{console.error(e);process.exit(1)});
