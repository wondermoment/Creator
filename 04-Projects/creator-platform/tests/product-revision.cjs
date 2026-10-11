const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/product-editor.js','utf8');
function setup(revision){
  const requests=[];let handler;
  const ctx={AbortController,setTimeout,clearTimeout,esc:v=>String(v??''),money:String,crypto:{randomUUID:()=> 'new'},document:{addEventListener(){}},window:{addEventListener(){}},showForm(t,h,s,fn){handler=fn},api:async(path,opts)=>{requests.push({path,body:JSON.parse(opts.body)});throw Error('conflict')},fixture:{id:'custom-one',name:'合成',price:100,stock:4,category:'食物',status:'draft',revision}};
  vm.createContext(ctx);vm.runInContext(source,ctx);vm.runInContext('managedProducts=[fixture]',ctx);
  return {ctx,requests,submit:()=>handler(new Map([['price','1.00'],['stock','4'],['name','合成']]))};
}
(async()=>{
  const h=setup('a'.repeat(64));h.ctx.productEdit('custom-one');
  // Updating the list while the dialog is open must not silently adopt a newer revision.
  vm.runInContext('managedProducts=[{...fixture,revision:"b".repeat(64)}]',h.ctx);
  await assert.rejects(h.submit(),/conflict/);
  assert.equal(h.requests[0].body.expected_revision,'a'.repeat(64));
  const legacy=setup(undefined);legacy.ctx.productEdit('custom-one');
  await assert.rejects(legacy.submit(),/版本尚未加载/);assert.equal(legacy.requests.length,0);
  const fresh=setup(undefined);fresh.ctx.productEdit();await assert.rejects(fresh.submit(),/conflict/);
  assert.equal(fresh.requests[0].path,'/commerce/products/custom-new');
  assert.ok(!('expected_revision' in fresh.requests[0].body));
  console.log('PASS: captured edit revision retained, missing revision blocks save, new products remain creatable');
})().catch(e=>{console.error(e);process.exit(1)});
