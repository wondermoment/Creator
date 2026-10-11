const fs=require('fs'),vm=require('vm'),assert=require('assert');
let requests=[],renders=0,closes=0,notices=0,save;
const c=vm.createContext({Map,Set,JSON,URLSearchParams,pid:'p',me:{identity:'alice'},state:{knowledge:[]},location:{hash:'#qa?view=evidence'},document:{addEventListener(){}},qaPage(){},brandPage(){},refresh:async()=>{},page:()=> 'qa',render:()=>renders++,api:(url,method,body)=>new Promise((resolve,reject)=>requests.push({url,method,body,resolve,reject})),openModal:(t,b,f,s)=>save=s,closeModal:()=>closes++,toast:()=>notices++,esc:s=>s||'',selectOptions:()=>'',err:()=>''});
vm.runInContext(fs.readFileSync('static/qa.js','utf8'),c);const run=s=>vm.runInContext(s,c);
const form={getAll:()=>[],get:k=>({question:'客户问题',answer:'草稿答案',category:'产品问答'})[k]};
(async()=>{
 run("Object.assign(qaSession(),{query:'alice private',selected:['a'],pending:true})");
 const first=run('qaLookup()');assert.equal(requests[0].body.query,'alice private');
 run("me.identity='bob'");assert.equal(run('qaSession().query'),'');assert.equal(run('qaSession().selected.length'),0);assert.equal(run('qaSession().pending'),false);
 const count=renders;requests[0].resolve({matches:[{id:'secret'}]});await first;assert.equal(renders,count);assert.equal(run('qaSession().result'),null);
 run("me.identity='alice'");assert.equal(run('qaSession().result'),null);assert.equal(run('qaSession().busy'),false);assert.equal(run('qaSession().query'),'alice private');
 const old=run('qaLookup()');run("qaSession().query='new query'");const latest=run('qaLookup()');requests[2].resolve({matches:[{id:'latest'}]});await latest;requests[1].resolve({matches:[{id:'old'}]});await old;assert.equal(run('qaSession().result.matches[0].id'),'latest');
 const failed=run('qaLookup()');run("me.identity='bob'");requests[3].reject(Error('alice-only-error'));await failed;assert.equal(run('qaSession().error'),'');run("me.identity='alice'");assert.equal(run('qaSession().error'),'');
 run("pid='other'");assert.equal(run('qaSession().query'),'');run("pid='p';faqModal()");const blocked=save;run("me.identity='bob'");await assert.rejects(blocked(form),/切换/);assert.equal(requests.length,4);
 run("me.identity='alice';faqModal()");const saving=save(form);run("me.identity='bob'");requests[4].resolve({id:'created'});await saving;assert.equal(closes,0);assert.equal(notices,0);
 run("me.identity='alice';faqModal()");const valid=save(form);requests[5].resolve({id:'created'});await valid;assert.equal(closes,1);assert.equal(notices,1);
 console.log('PASS: per-member and enterprise queries/selections; out-of-order results; late success/error suppression; modal submit and completion scope guards');
})().catch(e=>{console.error(e);process.exitCode=1});
