const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/product-editor.js','utf8');
const app=fs.readFileSync('frontend/app.js','utf8');
const formCode=app.slice(app.indexOf('let formGeneration='),app.indexOf('\nfunction record()'));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
function setup(){
 const requests=[],timers=new Map(),transport=deferred(),nodes={};let n=0,refreshes=0,toastCount=0;
 for(const id of ['modal','form','submit','form-error','modal-title','fields'])nodes['#'+id]={};
 nodes['#modal'].showModal=function(){this.open=true};nodes['#modal'].close=function(){this.open=false};
 const fields=new Map([['name','合成商品'],['price','1.00'],['stock','3'],['status','draft']]);
 const ctx={AbortController,esc:String,money:String,crypto:{randomUUID:()=> 'synthetic'},document:{addEventListener(){}},window:{addEventListener(){}},$:s=>nodes[s],FormData:class{constructor(){return fields}},render(){},toast(){toastCount++},setTimeout(fn){timers.set(++n,fn);return n},clearTimeout(id){timers.delete(id)},api(path,opts){requests.push({path,opts});return transport.promise}};
 vm.createContext(ctx);vm.runInContext(source,ctx);vm.runInContext(formCode,ctx);
 ctx.loadManagedProducts=ctx.commerceLoad=()=>{refreshes++;return new Promise(()=>{})};
 ctx.productEdit();
 return {ctx,nodes,requests,timers,transport,fields,get refreshes(){return refreshes},get toasts(){return toastCount},submit:()=>nodes['#form'].onsubmit({preventDefault(){},target:{}}),expire(){for(const fn of [...timers.values()])fn()}};
}
(async()=>{
 const hung=setup(),pending=hung.submit();assert.equal(hung.nodes['#submit'].disabled,true);hung.expire();await pending;
 assert.equal(hung.nodes['#modal'].open,true);assert.equal(hung.nodes['#submit'].disabled,false);
 assert.match(hung.nodes['#form-error'].textContent,/30秒/);assert.match(hung.nodes['#form-error'].textContent,/custom-synthetic/);
 assert.equal(hung.requests[0].opts.signal.aborted,true);assert.equal(hung.timers.size,0);assert.equal(hung.fields.get('name'),'合成商品');
 hung.fields.set('name','用户修改');await hung.submit();assert.equal(hung.requests.length,1);assert.match(hung.nodes['#form-error'].textContent,/核对上次保存结果/);
 hung.transport.resolve({id:'custom-synthetic',status:'draft'});await Promise.resolve();assert.equal(hung.refreshes,0);assert.equal(hung.toasts,0);assert.equal(hung.nodes['#modal'].open,true);
 for(const result of [null,{}, {id:'custom-other',status:'draft'},{id:'custom-synthetic',status:'published'}]){
  const bad=setup(),saving=bad.submit();bad.transport.resolve(result);await saving;assert.match(bad.nodes['#form-error'].textContent,/结果不完整/);assert.equal(bad.nodes['#modal'].open,true);assert.equal(bad.timers.size,0);
 }
 const ok=setup(),save=ok.submit();ok.transport.resolve({id:'custom-synthetic',status:'draft'});await save;
 assert.equal(ok.refreshes,2);assert.equal(ok.nodes['#modal'].open,false);assert.equal(ok.toasts,1);assert.equal(ok.timers.size,0);
 for(const message of ['network','商品内容或库存已变更']){
  const bad=setup(),saving=bad.submit();bad.transport.reject(Error(message));await saving;assert.ok(bad.nodes['#form-error'].textContent.includes(message));assert.equal(bad.nodes['#modal'].open,true);assert.equal(bad.nodes['#submit'].disabled,false);
 }
 console.log('PASS: actual shared form recovers from hung/failed/invalid save; preserves form, blocks blind retry, ignores late success; confirmed save completes despite both refreshes hanging');
})().catch(e=>{console.error(e);process.exit(1)});
