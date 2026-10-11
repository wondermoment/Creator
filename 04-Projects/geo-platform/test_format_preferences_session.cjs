const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={},calls=[];let save,closed=0,refreshed=0,toasts=0;
const ctx=vm.createContext({Map,Set,JSON,Date,epoch:1,pid:'p',me:{identity:'alice'},state:{format_skill:[]},
 document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},esc:s=>s,err:()=>'',canEdit:()=>true,
 openModal:(title,html,flag,cb)=>{save=cb},closeModal:()=>closed++,refresh:async()=>refreshed++,toast:()=>toasts++,
 api:async(...args)=>{calls.push(args)}});
vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),ctx);
vm.runInContext('refresh=async()=>{}',ctx);
const open=()=>listeners.click.forEach(f=>{if(f.toString().includes('repurpose-preferences'))f({target:{closest:()=>({dataset:{id:'moments'}})}})});
const values={get:()=> '简洁自然'};
(async()=>{
 open();ctx.me.identity='bob';await assert.rejects(save(values));assert.equal(calls.length,0);
 ctx.me.identity='alice';open();ctx.epoch++;await assert.rejects(save(values));assert.equal(calls.length,0);
 open();ctx.pid='other';await assert.rejects(save(values));assert.equal(calls.length,0);ctx.pid='p';
 open();let finish;ctx.api=async(...args)=>{calls.push(args);return new Promise(r=>finish=r)};
 const pending=save(values);ctx.me.identity='bob';finish({});await pending;assert.equal(closed,0);assert.equal(toasts,0);
 ctx.me.identity='alice';ctx.api=async(...args)=>calls.push(args);open();await save(values);
 assert.equal(calls.length,2);assert.equal(closed,1);assert.equal(toasts,1);
 assert.equal(calls[1][0],'/api/projects/p/format-skills/moments');assert.equal(calls[1][2].requirements,'简洁自然');
 console.log('PASS: default preferences reject stale user, session, project; late success cannot close new user modal; normal save works');
})().catch(e=>{console.error(e);process.exitCode=1});
