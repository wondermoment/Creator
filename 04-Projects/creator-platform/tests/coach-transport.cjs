const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let abortSeen=false,scheduled=[],cleared=[];
const c={AbortController,document:{addEventListener(){}},setTimeout(fn,ms){scheduled.push({fn,ms});return scheduled.length},clearTimeout:id=>cleared.push(id),post(path,body,signal){assert.equal(path,'/coaches/nutrients/chat');assert.equal(body.question,'synthetic');assert(signal instanceof AbortSignal);signal.addEventListener('abort',()=>abortSeen=true);return new Promise(()=>{})}};
vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),c);vm.runInContext(fs.readFileSync('frontend/coach-chat.js','utf8'),c);
(async()=>{
 const p=c.coachRequest('/coaches/nutrients/chat',{question:'synthetic'});
 assert.equal(scheduled[0].ms,270000);scheduled[0].fn();await assert.rejects(p,/服务端可能仍在处理/);assert(abortSeen);assert.deepEqual(cleared,[1]);
 // Cancellation settles even if a transport ignores AbortSignal.
 let calls=0,resolveLate,receivedSignal;const external=new AbortController();
 c.post=(path,body,signal)=>{calls++;receivedSignal=signal;return new Promise(resolve=>resolveLate=resolve)};
 const waiting=c.coachRequest('/books/synthetic/chat',{question:'synthetic'},external.signal);
 external.abort();await assert.rejects(waiting,/等待已取消/);assert(receivedSignal.aborted);assert.equal(calls,1);assert.equal(cleared.length,2);
 resolveLate({answer:'late'});await Promise.resolve();
 const timerCount=scheduled.length;
 await assert.rejects(c.coachRequest('/books/synthetic/chat',{},external.signal),/等待已取消/);assert.equal(calls,1);assert.equal(scheduled.length,timerCount);
 // Successful completion removes the external listener: later abort has no effect.
 const completed=new AbortController();c.post=async(path,body,signal)=>{receivedSignal=signal;return {answer:'ok'}};
 assert.equal((await c.coachRequest('/books/synthetic/chat',{},completed.signal)).answer,'ok');
 completed.abort();assert(!receivedSignal.aborted);
 c.post=()=>{throw Error('synchronous transport error')};const count=cleared.length;
 await assert.rejects(c.coachRequest('/books/synthetic/chat',{},new AbortController().signal),/synchronous transport/);assert.equal(cleared.length,count+1);
 // Execute the actual api/post definitions to verify AbortSignal reaches fetch.
 const app=fs.readFileSync('frontend/app.js','utf8'),start=app.indexOf('async function api('),end=app.indexOf('function toast(');
 let got;const a={FormData,fetch:async(url,options)=>{got={url,options};return {ok:true,json:async()=>({answer:'synthetic'})}}};vm.createContext(a);vm.runInContext(app.slice(start,end)+'\nthis.testPost=post;',a);
 const ctl=new AbortController();await a.testPost('/coaches/nutrients/chat',{question:'synthetic'},ctl.signal);assert.equal(got.options.signal,ctl.signal);assert.equal(got.options.method,'POST');assert.equal(got.options.body,JSON.stringify({question:'synthetic'}));
 await a.testPost('/other',{value:1});assert.ok(!('signal' in got.options));
 console.log('PASS: 270-second boundary aborts browser transport; api forwards signal; unrelated POST callers unchanged. Synthetic timers/network only.');
})().catch(e=>{console.error(e);process.exit(1)});
