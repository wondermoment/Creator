const fs=require('fs'),vm=require('vm'),assert=require('assert');
const output={innerHTML:'initial'},form={querySelector:()=>null,querySelectorAll:()=>[]};
let route='repurpose',syncs=0;const listeners={};
const ctx=vm.createContext({console,Map,Set,JSON,Date,epoch:1,pid:'a',me:{identity:'alice'},state:{marker:'initial',content:[],execution:[]},document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},page:()=>route,$:s=>s==='#repurpose-results'?output:form,canEdit:()=>true,refresh:async()=>{},syncManager:()=>syncs++});
vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
function pending(){let resolve,reject;ctx.api=()=>new Promise((a,b)=>{resolve=a;reject=b});return {promise:run('refresh()'),resolve:v=>resolve({marker:v,content:[],execution:[]}),reject};}
(async()=>{
 let p=pending();ctx.me.identity='bob';p.resolve('alice-response');await p.promise;assert.equal(ctx.state.marker,'initial');assert.equal(syncs,0);
 ctx.me.identity='alice';p=pending();ctx.pid='b';p.resolve('wrong-project');await p.promise;assert.equal(ctx.state.marker,'initial');ctx.pid='a';
 p=pending();ctx.epoch++;p.resolve('previous-session');await p.promise;assert.equal(ctx.state.marker,'initial');
 const older=pending(),newer=pending();newer.resolve('newest');await newer.promise;older.resolve('old');await older.promise;assert.equal(ctx.state.marker,'newest');
 p=pending();ctx.me.identity='bob';p.reject(Error('old error'));await p.promise;assert.equal(ctx.state.marker,'newest');
 p=pending();p.reject(Error('current error'));await assert.rejects(p.promise,/current error/);
 p=pending();route='workspace';p.resolve('left-page');await p.promise;assert.equal(ctx.state.marker,'newest');route='repurpose';
 p=pending();run('clearRepurposeSession()');p.resolve('before-logout');await p.promise;assert.equal(ctx.state.marker,'newest');
 run("repurposeEditors.set(repurposeEditKey('job'),{body:'unsaved'})");output.innerHTML='unsaved editor';p=pending();p.resolve('valid');await p.promise;assert.equal(ctx.state.marker,'valid');assert.equal(output.innerHTML,'unsaved editor');
 run('repurposeEditors.clear()');
 const input=value=>listeners.input.forEach(f=>f({target:{name:'feedback',value,closest:s=>s==='.repurpose-rewrite-form'?{dataset:{job:'job'}}:null}}));
 input('保留这个修改要求');output.innerHTML='editing feedback';p=pending();p.resolve('while-typing');await p.promise;assert.equal(output.innerHTML,'editing feedback');
 input('');p=pending();p.resolve('cleared');await p.promise;assert.notEqual(output.innerHTML,'editing feedback','clearing feedback must resume result updates');
 assert.equal(run('repurposeFeedback.size'),0);
 console.log('PASS: repurpose refresh user/project/session isolation, request ordering, stale errors, logout invalidation and editor preservation');
})().catch(e=>{console.error(e);process.exitCode=1});
