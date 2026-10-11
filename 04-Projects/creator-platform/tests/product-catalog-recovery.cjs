const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/product-editor.js','utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const row=(name='合成商品')=>({id:'custom-test',name,category:'食物',description:'合成说明',ingredients:'合成规格',usage:'合成用法',cautions:'合成限制',price:100,stock:3,status:'published',has_image:0,revision:'a'.repeat(64)});
function setup(){const requests=[],timers=new Map();let n=0;const ctx={AbortController,esc:String,money:String,shopFilter:'全部',state:{overview:true,page:'commerce'},render(){},document:{addEventListener(){}},window:{addEventListener(){}},setTimeout(fn){timers.set(++n,fn);return n},clearTimeout(id){timers.delete(id)},api(path,opts){const d=deferred();requests.push({...d,path,opts});return d.promise}};vm.createContext(ctx);vm.runInContext(source,ctx);return {ctx,requests,timers,read:code=>vm.runInContext(code,ctx),expire(){for(const fn of [...timers.values()])fn()}}}
(async()=>{
 const h=setup();const old=h.ctx.loadManagedProducts(),newer=h.ctx.loadManagedProducts();assert.equal(h.requests[0].opts.signal.aborted,true);
 h.requests[1].resolve([row('新商品')]);await newer;h.requests[0].resolve([row('旧商品')]);await old;
 assert.equal(h.read('managedProducts[0].name'),'新商品');assert.equal(h.timers.size,0);
 const hung=h.ctx.loadManagedProducts();assert.match(h.ctx.managedCatalog(),/上次读取/);assert.match(h.ctx.managedCatalog(),/data-product-edit="custom-test" disabled/);
 h.expire();await hung;assert.match(h.read('managedProductError'),/15秒/);assert.equal(h.requests[2].opts.signal.aborted,true);assert.equal(h.read('managedProducts[0].name'),'新商品');assert.equal(h.timers.size,0);
 assert.match(h.ctx.managedShopCards(),/刷新商品/);
 h.requests[2].resolve([row('超时迟到')]);await Promise.resolve();assert.equal(h.read('managedProducts[0].name'),'新商品');
 for(const bad of [null,{},[null],[{...row(),stock:-1}],[{...row(),description:null}],[{...row(),revision:undefined}],[row(),row()]]){
  const task=h.ctx.loadManagedProducts();h.requests.at(-1).resolve(bad);await task;assert.match(h.read('managedProductError'),/数据不完整/);assert.equal(h.read('managedProducts[0].name'),'新商品');
 }
 const retry=h.ctx.loadManagedProducts();h.requests.at(-1).resolve([]);await retry;assert.equal(h.read('managedProductError'),'');assert.match(h.ctx.managedCatalog(),/还没有自建商品/);assert.equal(h.ctx.managedShopCards(),'');
 const first=setup();const fail=first.ctx.loadManagedProducts();first.requests[0].reject(Error('network'));await fail;assert.ok(!first.ctx.managedCatalog().includes('还没有自建商品'));assert.equal(first.timers.size,0);
 console.log('PASS: superseded and timeout results isolated, malformed data preserves last list, controls/status/empty state and retry recover');
})().catch(e=>{console.error(e);process.exit(1)});
