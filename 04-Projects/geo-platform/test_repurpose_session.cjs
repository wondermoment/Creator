const fs=require('fs'),vm=require('vm'),assert=require('assert');
const storage=new Map();const sessionStorage={get length(){return storage.size},key:i=>[...storage.keys()][i],getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
function boot(user='user-a',project='enterprise-a',store=sessionStorage){
 const listeners={},button={},notice={},inputs=['article','moments','short_video'].map(value=>({value}));
 const form={id:'repurpose-form',querySelector:s=>s==='#repurpose-recovery'?notice:button,querySelectorAll:s=>s==='[name="formats"]'?inputs:[]};
 const c=vm.createContext({console,Map,Set,JSON,Date,crypto:require('crypto').webcrypto,sessionStorage:store,me:{identity:user},pid:project,state:{role:'owner',content:[{id:'source',revision:1}]},document:{addEventListener(t,f){(listeners[t]??=[]).push(f)}},page:()=> 'repurpose',$:()=>form,canEdit:()=>true,refresh:async()=>{},syncManager:()=>{},toast:()=>{}});
 vm.runInContext(fs.readFileSync('static/repurpose.js','utf8'),c);vm.runInContext('refresh=async()=>{}',c);
 c.formSubmit=(_,fn)=>{const d=JSON.parse(vm.runInContext('JSON.stringify(repurposeDraft())',c));c.pending=fn({get:k=>d[k],getAll:()=>d.formats}).catch(e=>c.error=e.message);return c.pending;};
 c.fire=()=>listeners.submit[0]({target:form,preventDefault(){}});return c;
}
const read=c=>JSON.parse(vm.runInContext('JSON.stringify(repurposeDraft())',c));
const settle=async c=>{await c.pending;await Promise.resolve();await Promise.resolve()};
(async()=>{
 let a=boot(),key,calls=[];
 vm.runInContext("Object.assign(repurposeDraft(),{source:'source',question:'保留条件与限制',formats:['article','moments','short_video']})",a);
 a.api=async(_,__,body)=>{calls.push(body);if(body.repurpose_channel==='moments'){key=body.request_key;throw Error('响应丢失')}return{id:'one'}};
 a.fire();await settle(a);assert.deepEqual(read(a).formats,['moments','short_video']);
 a=boot();assert.deepEqual(read(a),{source:'source',topic:'',question:'保留条件与限制',formats:['moments','short_video']});assert(vm.runInContext('repurposeRecoveryNote()',a).includes('已恢复'));
 assert.equal(calls.length,2,'restoring cannot submit automatically');
 a.api=async(_,__,body)=>{calls.push(body);return{id:'existing'}};a.fire();await settle(a);
 assert.equal(calls[2].request_key,key,'page reload must reuse uncertain request key');assert.equal(read(boot()).formats.length,0,'successful options stay cleared after reload');
 assert.equal(read(boot('user-b')).question,'');assert.equal(read(boot('user-a','enterprise-b')).source,'');
 a.me={identity:'user-b'};assert.equal(read(a).question,'','in-memory drafts also scoped to account');
 const savedKey=[...storage.keys()][0];const record=JSON.parse(storage.get(savedKey));record.updated=Date.now()-25*3600000;storage.set(savedKey,JSON.stringify(record));assert.equal(read(boot()).source,'');assert(!storage.has(savedKey));
 storage.set(savedKey,'{broken');assert.equal(read(boot()).source,'');assert(!storage.has(savedKey));
 storage.set(savedKey,JSON.stringify({...record,updated:Date.now(),requests:[['["other-user","source",1,"q","moments"]','key']]}));assert.equal(read(boot()).source,'','foreign retry scope rejected');
 const blocked={get length(){throw Error('blocked')},getItem(){throw Error('blocked')},setItem(){throw Error('quota')},removeItem(){}};
 const b=boot('user-a','enterprise-a',blocked);vm.runInContext("repurposeDraft().question='keep';persistRepurpose()",b);assert.equal(read(b).question,'keep');assert(vm.runInContext('repurposeRecoveryNote()',b).includes('请勿刷新'));
 storage.set('unrelated','keep');vm.runInContext('clearRepurposeSession()',a);assert.deepEqual([...storage.keys()],['unrelated']);
 assert(fs.readFileSync('static/app.js','utf8').includes("if(typeof clearRepurposeSession==='function')clearRepurposeSession()"));
 console.log('PASS: reload resumes remaining batch with same request key; no auto-run; user/tenant isolation; expiry, corrupt storage, foreign scope, quota fallback and logout cleanup');
})().catch(e=>{console.error(e);process.exitCode=1});
