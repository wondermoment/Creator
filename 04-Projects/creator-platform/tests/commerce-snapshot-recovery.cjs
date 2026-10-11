const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/commerce.js','utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const snapshot=(stock=4)=>({mode:'sandbox',live_payment:false,products:[{id:'oats',name:'合成燕麦',price:100,stock}],agents:[],orders:[{id:'order-test',product_id:'oats',quantity:1,total:100,status:'pending'}],ledger:[],transfers:[],audit:[]});
function setup(){const requests=[],timers=new Map();let n=0,forms=0,writes=0,click;
 const ctx={AbortController,URLSearchParams,esc:String,date:String,location:{search:'',hash:'#commerce'},crypto:{randomUUID:()=> 'synthetic'},state:{page:'commerce'},render(){},managedCatalog:()=>'',inquiryAdmin:()=>'',toast(){},showForm(){forms++},window:{addEventListener(){}},document:{addEventListener(e,fn){click=fn}},setTimeout(fn){timers.set(++n,fn);return n},clearTimeout(id){timers.delete(id)},api(path,opts){const d=deferred();requests.push({...d,path,opts});return d.promise},post(){writes++;throw Error('Unexpected write')}};
 vm.createContext(ctx);vm.runInContext(source,ctx);return {ctx,requests,timers,read:code=>vm.runInContext(code,ctx),get forms(){return forms},get writes(){return writes},click:e=>click(e),expire(){for(const fn of [...timers.values()])fn()}};
}
(async()=>{
 const h=setup(),first=h.ctx.commerceLoad(),second=h.ctx.commerceLoad();assert.equal(h.requests[0].opts.signal.aborted,true);
 h.requests[1].resolve(snapshot(2));await second;h.requests[0].resolve(snapshot(9));assert.equal(await first,null);assert.equal(h.read('commerceData.products[0].stock'),2);assert.equal(h.timers.size,0);
 const timeout=h.ctx.commerceLoad();assert.match(h.ctx.commercePage(),/上次读取/);assert.match(h.ctx.commercePage(),/data-commerce-action="cancel" disabled/);h.expire();assert.equal(await timeout,null);assert.equal(h.ctx.commerceReady(),false);assert.equal(h.timers.size,0);h.requests[2].resolve(snapshot(10));await Promise.resolve();assert.equal(h.read('commerceData.products[0].stock'),2);
 const buying=h.ctx.commerceBuy('oats');h.requests.at(-1).reject(Error('network'));await assert.rejects(buying,/network/);assert.equal(h.forms,0);
 for(const bad of [null,{}, {...snapshot(),live_payment:true},{...snapshot(),orders:[null]},{...snapshot(),products:[{...snapshot().products[0],stock:-1}]},{...snapshot(),agents:[{id:'a',name:null,parent_id:null}]}]){
  const task=h.ctx.commerceLoad();h.requests.at(-1).resolve(bad);assert.equal(await task,null);assert.equal(h.read('commerceData.products[0].stock'),2);assert.match(h.ctx.commercePage(),/可能已过期/);
 }
 await h.click({target:{closest:()=>({disabled:false,dataset:{commerceOrder:'order-test'},hasAttribute:()=>false})}}); assert.equal(h.writes,0);
 const ok=h.ctx.commerceBuy('oats');h.requests.at(-1).resolve(snapshot(3));await ok;assert.equal(h.forms,1);assert.equal(h.ctx.commerceReady(),true);assert.equal(h.timers.size,0);
 const concurrent=h.ctx.commerceBuy('oats'),replacement=h.ctx.commerceLoad();h.requests.at(-1).resolve(snapshot(5));await replacement;await assert.rejects(concurrent,/尚未确认/);assert.equal(h.forms,1);
 console.log('PASS: snapshot supersession/timeout/validation, stale read-only display, purchase requires fresh success, and retry recovery');
})().catch(e=>{console.error(e);process.exit(1)});
