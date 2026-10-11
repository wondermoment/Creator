const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={};let handler,finish,sent;
const ctx=vm.createContext({Map,Set,JSON,Date,pid:'p',epoch:1,me:{identity:'a'},state:{content:[],execution:[]},
 document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},page:()=> 'repurpose',$:()=>null,canEdit:()=>true,
 refresh:async()=>{},toast:()=>{},formSubmit:(form,fn)=>{handler=fn();return handler},
 api:async(url,method,body)=>{sent=JSON.parse(JSON.stringify(body));return new Promise(r=>finish=r)}});
vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),ctx);vm.runInContext('refresh=async()=>{}',ctx);
const run=s=>vm.runInContext(s,ctx);
const fire=()=>listeners.submit.forEach(fn=>fn({target:{dataset:{job:'j'},matches:s=>s==='.repurpose-edit-form'},preventDefault(){}}));
(async()=>{
 run("repurposeEditors.set(repurposeEditKey('j'),{id:'c',title:'标题',body:'原文',revision:3,channels:[],scheduled:''})");
 fire();run("repurposeEditors.get(repurposeEditKey('j')).body='保存期间继续写'");finish({ok:true});await handler;
 assert.equal(sent.body,'原文');assert.equal(run("repurposeEditors.get(repurposeEditKey('j'))?.body"),'保存期间继续写');
 assert.equal(run("repurposeEditors.get(repurposeEditKey('j')).revision"),4);
 fire();finish({ok:true});await handler;assert.equal(sent.body,'保存期间继续写');assert.equal(sent.revision,4);assert.equal(run('repurposeEditors.size'),0);
 run("repurposeEditors.set(repurposeEditKey('j'),{id:'c',title:'标题',body:'旧会话',revision:5,channels:[],scheduled:''})");
 fire();ctx.epoch++;run("clearRepurposeSession();repurposeEditors.set(repurposeEditKey('j'),{body:'新会话输入'});repurposeSaving.add(repurposeEditKey('j'))");finish({ok:true});await handler;
 assert.equal(run("repurposeEditors.get(repurposeEditKey('j')).body"),'新会话输入');assert(run("repurposeSaving.has(repurposeEditKey('j'))"));
 console.log('PASS: edits typed during save preserved, confirmed version advances, unchanged save closes, stale session leaves new editor intact');
})().catch(e=>{console.error(e);process.exitCode=1});
