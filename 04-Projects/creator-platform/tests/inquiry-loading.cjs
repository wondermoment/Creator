// All records, requests, timers and mutations are synthetic. No running service is called.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('frontend/customer-service.js','utf8');
const row=(id='synthetic-1')=>({id,subject:'合成咨询',kind:'了解项目',need:'合成需求',created_at:'2026-10-05T00:00:00Z',status:'pending',timeline:[{at:'2026-10-05T00:00:00Z',status:'pending',note:'合成进度'}]});
function setup(){
 const requests=[],timers=new Map(),toasts=[];let seq=0,renders=0,forms=0;
 const c={AbortController,document:{addEventListener(){}},window:{addEventListener(){}},state:{overview:{},page:'account'},render(){renders++},toast:m=>toasts.push(m),showForm(){forms++},date:String,travelStored:()=>[],esc:x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'),setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,ms});return id},clearTimeout:id=>timers.delete(id),api:(path,options)=>new Promise((resolve,reject)=>requests.push({path,options,resolve,reject}))};
 vm.createContext(c);vm.runInContext(source,c);
 return {c,requests,timers,toasts,get renders(){return renders},get forms(){return forms},read:x=>vm.runInContext(x,c),tick(){for(const {fn,ms} of [...timers.values()]){assert.equal(ms,15000);fn()}}};
}
(async()=>{
 // Initial failure must stop the spinner, show manual recovery, never imply empty success.
 let h=setup(),p=h.c.loadInquiries();assert(h.c.inquiryLoadStatus().includes('正在读取'));assert(h.c.inquiryRefreshButton().includes('disabled'));
 h.requests[0].reject(Error('<synthetic network error>'));await p;
 assert(!h.read('inquiryLoading'));assert(!h.read('inquiryLoaded'));assert(h.c.serviceInquiryList().includes('&lt;synthetic network error&gt;'));
 assert(!h.c.serviceInquiryList().includes('正在读取'));assert(!h.c.inquiryCards().includes('暂无已提交'));assert(!h.c.inquiryRefreshButton().includes('disabled'));
 p=h.c.loadInquiries();h.requests[1].resolve([]);await p;assert(h.c.inquiryCards().includes('暂无已提交'));assert.equal(h.c.inquiryLoadStatus(),'');
 // Hung read reaches a deadline even when transport ignores AbortSignal; no auto retry or late mutation.
 h=setup();p=h.c.loadInquiries();h.tick();await p;assert(h.requests[0].options.signal.aborted);assert.equal(h.requests.length,1);assert(h.c.inquiryLoadStatus().includes('15秒'));
 h.requests[0].resolve([row('late')]);await Promise.resolve();assert.equal(h.read('inquiryRows.length'),0);assert.equal(h.timers.size,0);
 // Newer refresh wins and supersedes an older read without waiting for its transport.
 h=setup();const old=h.c.loadInquiries(),fresh=h.c.loadInquiries();await old;
 assert(h.requests[0].options.signal.aborted);assert(h.read('inquiryLoading'));h.requests[1].resolve([row('new')]);await fresh;
 h.requests[0].resolve([row('old')]);await Promise.resolve();assert.equal(h.read('inquiryRows[0].id'),'new');assert.equal(h.c.inquiryLoadStatus(),'');assert.equal(h.timers.size,0);
 // Invalid data never destroys last-known-good records or allows a stale admin update.
 for(const bad of [null,{},[{}],[{...row(),timeline:null}],[{...row(),status:'unexpected'}],[{...row(),timeline:[{status:'pending'}]}]]){
  h=setup();p=h.c.loadInquiries();h.requests[0].resolve([row()]);await p;
  p=h.c.loadInquiries();assert(h.c.inquiryAdmin().includes('disabled'));h.c.inquiryFollow('synthetic-1');assert.equal(h.forms,0);
  h.requests[1].resolve(bad);await p;assert.equal(h.read('inquiryRows[0].id'),'synthetic-1');assert(h.c.inquiryLoadStatus().includes('上次读取'));assert(h.c.inquiryAdmin().includes('disabled'));
  h.c.inquiryFollow('synthetic-1');assert.equal(h.forms,0);assert.equal(h.requests.length,2);
  p=h.c.loadInquiries();h.requests[2].resolve([row('recovered')]);await p;assert.equal(h.c.inquiryLoadStatus(),'');assert(!h.c.inquiryAdmin().includes('disabled'));
 }
 // Navigating elsewhere doesn't repaint that page when an old list request completes.
 h=setup();p=h.c.loadInquiries();const renders=h.renders;h.c.state.page='diet';h.requests[0].resolve([]);await p;assert.equal(h.renders,renders);
 assert(h.requests.every(r=>r.path==='/commerce/inquiries'&&!r.options.method&&!r.options.body));
 console.log('PASS: inquiry GET deadline, supersession, stale-result isolation, manual recovery, malformed-response preservation, escaped errors and stale-admin guard. Synthetic only; no model or data writes.');
})().catch(e=>{console.error(e);process.exit(1)});
