const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup(){
 let resolveFetch,resolveRead,transportSignal,cancels=0;const timers=new Map();let serial=0;
 const reader={read:()=>new Promise(resolve=>{resolveRead=resolve}),cancel:async()=>{cancels++}};
 const c={AbortController,TextDecoder,Uint8Array,setTimeout(fn){timers.set(++serial,fn);return serial},clearTimeout(id){timers.delete(id)},requestErrorMessage:()=> 'failed',
 fetch(url,options){transportSignal=options.signal;return new Promise(resolve=>{resolveFetch=resolve})}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/chat-stream.js','utf8'),c);
 return {c,timers,resolveFetch:()=>resolveFetch({ok:true,body:{getReader:()=>reader}}),resolveRead:value=>resolveRead(value),get signal(){return transportSignal},get cancels(){return cancels}};
}
(async()=>{
 const first=setup(),already=new AbortController();already.abort();
 await assert.rejects(first.c.coachStreamRequest('/test',{},()=>{},already.signal),/已关闭/);assert.equal(first.signal,undefined);
 for(const phase of ['fetch','read','timeout']){
  const h=setup(),controller=new AbortController(),updates=[];
  const promise=h.c.coachStreamRequest('/test',{},text=>updates.push(text),controller.signal);
  // Attach before rejecting, including when mocked transport ignores abort.
  const rejected=assert.rejects(promise,phase==='timeout'?/超时/:/已关闭/);
  if(phase!=='fetch'){h.resolveFetch();await tick()}
  if(phase==='timeout')[...h.timers.values()][0]();else controller.abort();
  await rejected;assert(h.signal.aborted);assert.equal(h.timers.size,0);
  if(phase==='fetch')h.resolveFetch();
  else h.resolveRead({done:false,value:new TextEncoder().encode('{"type":"delta","delta":"迟到的文本"}\n')});
  await tick();assert.equal(updates.length,0);
  if(phase!=='fetch')assert(h.cancels>=1);
 }
 console.log('PASS: pre-abort, hung fetch/read cancellation, timeout cleanup, late delta suppression');
})().catch(e=>{console.error(e);process.exit(1)});
