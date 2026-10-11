const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/product-editor.js','utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
function setup(){
 const readers=[],timers=new Map(),requests=[];let nextTimer=0,current,handler;
 const modal={open:true,handlers:[],addEventListener(e,f){this.handlers.push(f)},close(){this.open=false;for(const f of this.handlers.splice(0))f()}};
 const transport=deferred();
 const ctx={AbortController,document:{addEventListener(){},querySelector(s){return s==='#modal'?modal:s.includes('input')?current.input:current.img}},window:{addEventListener(){}},state:{overview:false},
  showForm(t,h,l,fn){if(current){current.img.isConnected=false;current.input.isConnected=false}modal.open=true;current={img:{hidden:true,isConnected:true,removeAttribute(){delete this.src}},input:{files:[],isConnected:true,addEventListener(e,f){this.change=f}}};handler=fn},
  setTimeout(fn){const id=++nextTimer;timers.set(id,fn);return id},clearTimeout(id){timers.delete(id)},
  api(path,opts){requests.push({path,opts});return path.endsWith('/image')?transport.promise:new Promise(()=>{})},
  FileReader:class{constructor(){this.readyState=0;readers.push(this)}readAsDataURL(f){this.file=f;this.readyState=1}abort(){this.aborted=true;this.readyState=2}}
 };vm.createContext(ctx);vm.runInContext(source,ctx);
 return {ctx,modal,readers,timers,requests,transport,get current(){return current},submit:()=>handler({get:()=>({size:20})}),choose(file){current.input.files=file?[file]:[];current.input.change()},expire(){for(const fn of [...timers.values()])fn()}};
}
(async()=>{
 const h=setup();h.ctx.productImageUpload('custom-one');h.choose({size:20,name:'first'});const first=h.readers[0];h.choose({size:20,name:'second'});const second=h.readers[1];
 assert.equal(first.aborted,true);second.result='second-image';second.onload();first.result='stale-image';first.onload();assert.equal(h.current.img.src,'second-image');
 h.choose({size:6*1024*1024});assert.equal(h.current.img.hidden,true);assert.equal(h.current.img.src,undefined);
 h.choose({size:20});const old=h.readers.at(-1);h.ctx.productImageUpload('custom-two');old.result='old-window';old.onload();assert.equal(h.current.img.src,undefined);
 h.choose({size:20});const closing=h.readers.at(-1);h.modal.close();closing.result='late-close';closing.onload();assert.equal(closing.aborted,true);assert.equal(h.current.img.src,undefined);
 const timeout=setup();timeout.ctx.productImageUpload('custom-one');const pending=timeout.submit();timeout.expire();await assert.rejects(pending,/未能确认主图是否保存/);assert.equal(timeout.requests[0].opts.signal.aborted,true);assert.equal(timeout.timers.size,0);
 await assert.rejects(timeout.submit(),/先关闭窗口/);assert.equal(timeout.requests.length,1);timeout.transport.resolve({ok:true});await Promise.resolve();assert.equal(timeout.requests.length,1);
 for(const result of [null,{}, {ok:false}]){const bad=setup();bad.ctx.productImageUpload('custom-one');const task=bad.submit();bad.transport.resolve(result);await assert.rejects(task,/返回的上传结果不完整/);assert.equal(bad.timers.size,0)}
 const success=setup();success.ctx.productImageUpload('custom-one');const done=success.submit();success.transport.resolve({ok:true});await done;assert.equal(success.requests.length,2);assert.equal(success.requests[1].path,'/commerce/catalog');assert.equal(success.timers.size,1);success.expire();await new Promise(resolve=>setImmediate(resolve));assert.equal(success.timers.size,0);
 const failure=setup();failure.ctx.productImageUpload('custom-one');const failed=failure.submit();failure.transport.reject(Error('network'));await assert.rejects(failed,/服务端可能已处理/);assert.equal(failure.timers.size,0);
 console.log('PASS: preview replacement/invalid file/closed window isolation; timeout, late result, unknown-result retry guard; success independent of catalog wait');
})().catch(e=>{console.error(e);process.exit(1)});
