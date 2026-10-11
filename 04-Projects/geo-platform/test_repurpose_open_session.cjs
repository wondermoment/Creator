const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={};let finish,notices=[];
const button={dataset:{id:'j'},isConnected:true,disabled:false};
const ctx=vm.createContext({Map,Set,JSON,Date,pid:'p',epoch:1,me:{identity:'a'},state:{content:[],execution:[{id:'j',status:'succeeded',payload:{workflow:'repurpose'},result:{answer:'结果'}}]},
 document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},page:()=> 'repurpose',$:()=>null,canEdit:()=>true,refresh:async()=>{},toast:s=>notices.push(s),
 api:async()=>new Promise(r=>finish=r)});
vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),ctx);vm.runInContext('refresh=async()=>{}',ctx);
const run=s=>vm.runInContext(s,ctx),click=listeners.click.find(f=>f.toString().includes('repurpose-save'));
const open=()=>click({target:{closest:s=>s.includes('repurpose-save')?button:null}});
(async()=>{
 const pending=open();ctx.epoch++;run("clearRepurposeSession();repurposeEditors.set(repurposeEditKey('j'),{body:'新会话编辑'});repurposeSaving.add(repurposeEditKey('j'))");
 ctx.state.content=[{id:'c',repurpose_job_id:'j',title:'标题',body:'已保存正文',revision:1}];finish({id:'c'});await pending;
 assert.equal(run("repurposeEditors.get(repurposeEditKey('j')).body"),'新会话编辑');assert(run("repurposeSaving.has(repurposeEditKey('j'))"));assert.equal(notices.length,0);
 run('repurposeSaving.clear();repurposeEditors.clear()');await open();assert.equal(run("repurposeEditors.get(repurposeEditKey('j')).body"),'已保存正文');
 console.log('PASS: old draft-creation response cannot replace same-user new session editor; existing draft opens normally');
})().catch(e=>{console.error(e);process.exitCode=1});
