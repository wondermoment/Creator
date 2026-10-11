const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={},nodes=new Map(),node=s=>{if(!nodes.has(s))nodes.set(s,{innerHTML:'',value:'',textContent:'',disabled:false,addEventListener(){},querySelector:node,classList:{add(){},remove(){}}});return nodes.get(s)};
const c=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector:node,addEventListener(t,f){(listeners[t]??=[]).push(f)},hidden:false},window:{addEventListener(){}},location:{hash:'#skills?expert=content'},localStorage:{getItem(){return null}},setTimeout(){},setInterval(){},clearTimeout(){}});
for(const f of ['app','planning','knowledge','manager','leads','delivery','sample','experts'])vm.runInContext(fs.readFileSync(`static/${f}.js`,'utf8'),c);
const run=s=>vm.runInContext(s,c);c.notices=[];c.refreshes=0;c.question='发送此需求';
run("pid='a';me={identity:'alice'};activeExpert='content';state={role:'owner',execution:[]};toast=x=>notices.push(x);refresh=async()=>{refreshes++}");
const submit=listeners.submit.find(f=>f.toString().includes("e.target.id!=='expert-chat-form'")),button={disabled:false},form={id:'expert-chat-form',isConnected:true,querySelector:()=>button};
c.fields={get:k=>k==='question'?c.question:'faq',getAll:()=>[]};c.pending=null;c.failure=null;
run('formSubmit=(_,fn)=>{pending=fn(fields).catch(e=>{failure=e.message});return pending}');
function send(){let resolve,reject;c.api=()=>new Promise((a,b)=>{resolve=a;reject=b});submit({target:form,preventDefault(){}});return {promise:c.pending,resolve,reject};}
(async()=>{
 run("expertDraft().text='alice private';expertDraft().skill='video';me.identity='bob'");assert.equal(run('expertDraft().text'),'','unsent drafts must not cross accounts');assert.notEqual(run('expertDraft().skill'),'video');
 run("me.identity='alice'");assert.equal(run('expertDraft().text'),'alice private');run("activeExpert='technical'");assert.equal(run('expertDraft().text'),'');run("activeExpert='content';pid='b'");assert.equal(run('expertDraft().text'),'');run("pid='a'");
 let p=send();run("me.identity='bob';expertDraft().text='bob new'");assert(!run('expertBusy()'),'other user cannot inherit local sending state');node('#expert-message').value='bob new';p.resolve({id:'j'});await p.promise;assert.equal(run('expertDraft().text'),'bob new');assert.equal(node('#expert-message').value,'bob new');assert.equal(c.notices.length,0);assert.equal(c.refreshes,0);
 run("me.identity='alice';expertDraft().text='old'");p=send();run("expertDraft().text='typed during request'");node('#expert-message').value='typed during request';p.resolve({id:'j'});await p.promise;assert.equal(run('expertDraft().text'),'typed during request');assert.equal(node('#expert-message').value,'typed during request');
 p=send();run("me.identity='bob'");p.reject(Error('private old error'));await p.promise;assert.equal(c.failure,null);
 run("me.identity='alice'");p=send();run('clearExpertSession()');assert.equal(run('expertDraft().text'),'');const next=send();p.resolve({id:'old'});await p.promise;assert(run('expertBusy()'),'old finally cannot unlock new request');next.reject(Error('current failure'));await next.promise;assert.equal(c.failure,'current failure');assert(!run('expertBusy()'));
 run("expertDraft().text='to clear'");node('#expert-message').value='to clear';p=send();p.resolve({id:'new'});await p.promise;assert.equal(run('expertDraft().text'),'');assert.equal(node('#expert-message').value,'');
 assert(fs.readFileSync('static/app.js','utf8').includes("if(typeof clearExpertSession==='function')clearExpertSession()"));
 console.log('PASS: private draft/skill isolation, scoped sending, stale responses/errors, newer input preservation, logout cleanup and old request token safety');
})().catch(e=>{console.error(e);process.exitCode=1});
