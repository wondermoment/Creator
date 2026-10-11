const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),listeners={};
const node=k=>{if(!nodes.has(k))nodes.set(k,{innerHTML:'',value:'',open:true,isConnected:true,classList:{add(){},remove(){}},addEventListener(){},close(){this.open=false},showModal(){this.open=true},querySelector:node,querySelectorAll(){return []},insertAdjacentHTML(){}});return nodes.get(k)};
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector:node,addEventListener(t,f){(listeners[t]??=[]).push(f)},hidden:false},window:{addEventListener(){}},location:{hash:'#content'},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},clearTimeout(){},fetch(){throw Error('unexpected fetch')}});
for(const name of ['app','planning','knowledge','manager','leads','delivery','sample'])vm.runInContext(fs.readFileSync(`static/${name}.js`,'utf8'),ctx);
vm.runInContext(`pid='p1';previewId='c1';previewSnapshot={project:'p1',id:'c1',revision:2,ready:true};state={content:[{id:'c1',revision:99}]};`,ctx);
assert.equal(vm.runInContext(`previewRevision('c1')`,ctx),2,'review must use rendered revision, not refreshed state');
vm.runInContext(`previewSnapshot.ready=false`,ctx);assert.throws(()=>vm.runInContext(`previewRevision('c1')`,ctx),/完整加载/);
vm.runInContext(`previewSnapshot.ready=true;pid='p2'`,ctx);assert.throws(()=>vm.runInContext(`previewRevision('c1')`,ctx),/完整加载/);
vm.runInContext(`pid='p1';closeModal()`,ctx);assert.throws(()=>vm.runInContext(`previewRevision('c1')`,ctx),/完整加载/);

async function run(){
 let resolveImage,request,mode='ok';
 const controls=[{disabled:false}],target={innerHTML:'',textContent:'',isConnected:true,classList:{add(){}},insertAdjacentHTML(where,html){this.innerHTML=html+this.innerHTML},querySelectorAll:()=>[{decode:()=>new Promise((resolve,reject)=>{resolveImage=mode==='broken'?()=>reject(Error('decode failed')):resolve})}]};
 const sandbox=vm.createContext({pid:'p1',previewId:null,previewSnapshot:null,state:{content:[{id:'c1',layout:{}}]},modal:{querySelectorAll:()=>controls},$:()=>target,DOMParser:class {parseFromString(){return {querySelector:()=>({innerHTML:'<img>完整图文'})}}},fetch:async(url,opts)=>{request={url,opts};return {ok:mode!=='stale',status:mode==='stale'?409:200,headers:{get:name=>name==='X-Layout-Status'?(mode==='layout-stale'?'stale':'current'):'2'},text:async()=>'<article>完整图文</article>'}}});
 vm.runInContext("function preview(id){previewId=id;previewSnapshot={project:pid,id,revision:2,ready:false}}",sandbox);
 const source=fs.readFileSync('static/sample.js','utf8');vm.runInContext(source.slice(source.indexOf('const formattedProofBase=preview;')),sandbox);
 const flush=()=>new Promise(r=>setImmediate(r));
 vm.runInContext("preview('c1')",sandbox);await flush();
 assert(request.url.endsWith('?revision=2'));assert.equal(request.opts.cache,'no-store');
 assert(controls[0].disabled);assert(!sandbox.previewSnapshot.ready);
 resolveImage();await flush();assert(sandbox.previewSnapshot.ready);assert(!controls[0].disabled);
 mode='layout-stale';vm.runInContext("preview('c1')",sandbox);await flush();resolveImage();await flush();assert(!sandbox.previewSnapshot.ready);assert(controls[0].disabled);assert(target.innerHTML.includes('排版已过期'));
 mode='broken';vm.runInContext("preview('c1')",sandbox);await flush();resolveImage();await flush();
 assert(!sandbox.previewSnapshot.ready);assert(controls[0].disabled);assert(target.textContent.includes('配图加载失败'));
 mode='stale';vm.runInContext("preview('c1')",sandbox);await flush();assert(controls[0].disabled);assert(target.textContent.includes('版本已更新'));
 mode='ok';vm.runInContext("preview('c1')",sandbox);await flush();sandbox.pid='p2';resolveImage();await flush();assert(!sandbox.previewSnapshot.ready);assert(controls[0].disabled);
 console.log('PASS: review revision binding, close/tenant guard, HTML/image loading gate, broken-image and stale-version rejection');
}
run().catch(e=>{console.error(e);process.exitCode=1});
