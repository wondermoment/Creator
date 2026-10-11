const fs=require('fs'),vm=require('vm'),assert=require('assert');
const listeners={},calls=[];let save,closed=0,refreshed=0,editable=true;
const ctx=vm.createContext({Map,Set,JSON,epoch:1,pid:'p',me:{identity:'alice'},state:{seo_task:[{id:'task',version:3,status:'doing'}]},
 document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},esc:s=>s||'',err:()=>'',canEdit:()=>editable,
 openModal:(title,html,flag,cb)=>{save=cb},closeModal:()=>closed++,refresh:async()=>{},toast:()=>{},
 api:async(...args)=>calls.push(args)});
vm.runInContext(fs.readFileSync('static/seo.js','utf8'),ctx);ctx.refresh=async()=>refreshed++;
const open=()=>listeners.click[0]({target:{closest:()=>({dataset:{action:'seo-task-edit',id:'task'},isConnected:true})}});
const values={get:k=>({owner:'网站维护',note:'已处理，等待复测',status:'ready'})[k]};
(async()=>{
 await open();ctx.epoch++;await assert.rejects(save(values));assert.equal(calls.length,0);
 await open();ctx.me.identity='bob';await assert.rejects(save(values));assert.equal(calls.length,0);ctx.me.identity='alice';
 await open();ctx.pid='q';await assert.rejects(save(values));assert.equal(calls.length,0);ctx.pid='p';
 await open();editable=false;await assert.rejects(save(values));assert.equal(calls.length,0);editable=true;
 await open();let finish;ctx.api=async(...args)=>{calls.push(args);return new Promise(r=>finish=r)};
 const pending=save(values);ctx.epoch++;finish({});await pending;assert.equal(closed,0);assert.equal(refreshed,0);
 ctx.api=async(...args)=>calls.push(args);await open();await save(values);
 assert.equal(closed,1);assert.equal(refreshed,1);assert.equal(calls.length,2);
 assert.equal(calls[1][0],'/api/projects/p/seo-tasks/task');assert.equal(calls[1][2].version,3);assert.equal(calls[1][2].status,'ready');
 console.log('PASS: SEO task editor rejects changed session/user/project/permission; late response cannot close new modal; valid versioned save works');
})().catch(e=>{console.error(e);process.exitCode=1});
