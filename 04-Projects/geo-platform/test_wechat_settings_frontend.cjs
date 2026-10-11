const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),created=[],requests=[];
function make(){return {value:'',textContent:'',disabled:false,hidden:false,checked:false,style:{},after(){},append(){},setAttribute(){},removeAttribute(){},querySelector(){return node('save')}};}
function node(id){if(!nodes.has(id))nodes.set(id,make());return nodes.get(id);}
const context=vm.createContext({URLSearchParams,encodeURIComponent,console,
 location:{search:'?project=p1&content=c1&revision=8'},
 document:{getElementById:node,createElement(){const e=make();created.push(e);return e;}},
 fetch(url,options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}));}
});
vm.runInContext(fs.readFileSync('static/wechat-settings.js','utf8'),context);
const flush=()=>new Promise(r=>setImmediate(r));
const result=(r,d,ok=true)=>r.resolve({ok,json:async()=>d});
const cfg=id=>({appid:id,name:id,version:1,has_secret:true,status:'verified_read'});
const evaluate=s=>vm.runInContext(s,context);
async function main(){
 result(requests.shift(),{csrf:'fixture',projects:[{id:'p1',name:'One',role:'owner'},{id:'p2',name:'Two',role:'owner'}]});await flush();
 const first=requests.shift();assert.equal(first.url,'/api/projects/p1/wechat');
 assert(node('sync').disabled);assert(node('save').disabled);
 await node('test').onclick();assert.equal(requests.length,0,'no write while loading');
 node('project').value='p2';node('project').onchange();const second=requests.shift();
 assert.equal(second.url,'/api/projects/p2/wechat');result(second,cfg('SECOND'));await flush();
 assert.equal(node('appid').value,'SECOND');assert.equal(node('save').disabled,false);
 first.reject(Error('old tenant failed'));await flush();assert.equal(node('status').textContent,'企业：Two');
 assert(node('sync').disabled,'no target article in second tenant');
 node('secret').value='unsent-secret';node('project').value='p1';node('project').onchange();
 assert.equal(node('secret').value,'');assert(node('save').disabled);assert.equal(evaluate('config'),null);
 result(requests.shift(),cfg('FIRST'));await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 const receiptRequest=requests.shift();assert(node('sync').disabled,'article cannot submit before receipt/version load');
 node('confirm').checked=true;await node('sync').onclick();assert.equal(requests.length,0);
 node('project').value='p2';node('project').onchange();result(requests.shift(),cfg('SECOND'));await flush();
 result(receiptRequest,{revision:8,binding:{appid:'wx1234567890abcdef',version:1,name:'Fixture'},next_digest:'OLD',records:[{appid:'wx1234567890abcdef',id:'old',status:'needs_review',revision:8}]});await flush();
 assert(node('draft').hidden);assert.equal(evaluate('recoveryJob'),'');assert.equal(node('status').textContent,'企业：Two');
 node('project').value='p1';node('project').onchange();result(requests.shift(),cfg('FIRST'));await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 result(requests.shift(),{revision:9,binding:{appid:'wx1234567890abcdef',version:1,name:'Fixture'},next_digest:'NEW',records:[]});await flush();
 assert(node('sync').disabled);assert(node('draft').hidden);assert.equal(evaluate('readyProject'),'');
 node('project').onchange();result(requests.shift(),cfg('FIRST'));await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 result(requests.shift(),{revision:8,binding:{appid:'wx1234567890abcdef',version:1,name:'Fixture'},next_digest:'Correct',records:[]});await flush();
 assert(!node('sync').disabled);assert(!node('draft').hidden);assert(!node('confirm').checked);
 assert(created.find(x=>x.id==='target-preview').textContent.includes('Fixture · wx1234567890abcdef'));
 node('confirm').checked=true;const pending=node('sync').onclick();assert(node('project').disabled);assert(node('sync').disabled);
 const send=requests.shift();assert.equal(send.url,'/api/projects/p1/contents/c1/wechat-draft');assert.deepEqual(JSON.parse(send.options.body),{revision:8,confirm:true,appid:'wx1234567890abcdef',binding_version:1,template_version:0});
 await node('sync').onclick();assert.equal(requests.length,0,'duplicate click blocked');
 result(send,{id:'job',revision:8,status:'synced',media_id:'remote',synced_at:'2026-10-04T10:30:00+00:00'});await pending;
 assert(!node('project').disabled);assert(node('receipt').textContent.includes('已同步'));
 assert(node('receipt').textContent.includes('上次核对'));
 assert(node('receipt').textContent.includes('历史回执'));
 assert(!node('receipt').textContent.includes('尚未群发'),'receipt must not assert current remote publication status');
 const recheck=created.find(x=>x.textContent==='核对微信回执（不重发）');
 assert(!recheck.hidden&&!recheck.disabled,'synced receipts can be rechecked');
 const checking=recheck.onclick();const checkRequest=requests.shift();
 assert.equal(checkRequest.url,'/api/projects/p1/contents/c1/wechat-draft/job/reconcile');
 result(checkRequest,{detail:'远端内容与提交快照不一致，请在公众号核对'},false);await checking;
 assert(node('status').textContent.includes('远端内容与提交快照不一致'));
 assert(node('receipt').textContent.includes('历史回执'),'prior evidence remains historical');
 assert.equal(requests.length,0,'remote change must not trigger resend');
 assert(!node('confirm').checked,'every completed attempt clears confirmation');
 node('confirm').checked=true;const interrupted=node('sync').onclick();
 requests.shift().reject(Error('network lost'));await flush();
 assert(node('sync').disabled);assert(node('draft').hidden);assert(!node('confirm').checked);
 const refreshConfig=requests.shift();assert.equal(refreshConfig.options.method,'GET');
 result(refreshConfig,cfg('FIRST'));await flush();
 const refreshState=requests.shift();assert.equal(refreshState.options.method,'GET');
 result(refreshState,{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 const refreshReceipt=requests.shift();assert.equal(refreshReceipt.options.method,'GET');
 result(refreshReceipt,{revision:8,binding:{appid:'wx1234567890abcdef',version:1,name:'Fixture'},next_digest:'Correct',records:[{appid:'wx1234567890abcdef',id:'pending-job',revision:8,status:'needs_review'}]});await interrupted;
 assert(!node('receipt').textContent.includes('正在上传'));
 assert(node('status').textContent.includes('系统未自动重发'));
 assert(node('sync').disabled);assert(!recheck.disabled);
 node('confirm').checked=true;await node('sync').onclick();assert.equal(requests.length,0,'unresolved job blocks new submit');
 const recover=recheck.onclick();result(requests.shift(),{id:'pending-job',revision:8,status:'synced'});await recover;
 node('confirm').checked=true;const disconnected=node('sync').onclick();
 result(requests.shift(),{detail:'服务暂不可用'},false);await flush();
 requests.shift().reject(Error('still disconnected'));await disconnected;
 assert(node('sync').disabled);assert(node('draft').hidden);
 assert(node('status').textContent.includes('请刷新页面核对后再操作'));
 assert(!node('confirm').checked);assert.equal(requests.length,0);
 evaluate("me.projects[0].role='viewer'");node('project').onchange();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 result(requests.shift(),{revision:8,binding:{appid:'wx1234567890abcdef',version:1,name:'Fixture'},next_digest:'Correct',records:[{appid:'wx1234567890abcdef',id:'job',revision:8,status:'needs_review'}]});await flush();
 assert(node('sync').disabled);assert(created.find(x=>x.textContent==='核对微信回执（不重发）').disabled);
 evaluate("me.projects[0].role='owner'");node('project').onchange();
 result(requests.shift(),cfg('FIRST'));await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 result(requests.shift(),{revision:8,records:[]});await flush();
 assert(node('sync').disabled,'missing destination cannot submit');
 node('confirm').checked=true;await node('sync').onclick();assert.equal(requests.length,0);
 const saved=node('config-form').onsubmit({preventDefault(){}});result(requests.shift(),{...cfg('NEW'),version:2});await flush();
 assert(!node('confirm').checked,'saving binding invalidates prior confirmation');
 result(requests.shift(),{...cfg('NEW'),version:2});await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 result(requests.shift(),{revision:8,binding:{appid:'wx0000000000000000',version:2,name:'New account'},records:[{appid:'wx1234567890abcdef',id:'old-account',status:'needs_review',revision:8}]});await saved;
 assert(created.find(x=>x.id==='target-preview').textContent.includes('New account'));
 assert(created.find(x=>x.id==='target-preview').textContent.includes('另有 1 条'));
 assert.equal(evaluate('recoveryJob'),'');assert(recheck.hidden);
 assert.equal(node('receipt').textContent,'暂无同步记录','old account receipt cannot represent new destination');
 assert(!node('sync').disabled);assert(!node('confirm').checked);
 const records=[{appid:'other',id:'other-newest',status:'needs_review'},
  {appid:'current',id:'success',status:'synced'},
  {appid:'current',id:'blocked',status:'sending'},
  {id:'legacy',status:'needs_review'}];
 context.sampleRecords=records;
 assert.equal(evaluate("selectReceipt(sampleRecords,{appid:'current'}).id"),'blocked','older unresolved current account takes precedence');
 assert.equal(evaluate("selectReceipt(sampleRecords,{appid:'unbound'})"),null);
 assert.equal(evaluate('selectReceipt(sampleRecords,null)'),null);
 records[2].status='failed';
 assert.equal(evaluate("selectReceipt(sampleRecords,{appid:'current'}).id"),'success');
 node('project').onchange();result(requests.shift(),cfg('CURRENT'));await flush();
 result(requests.shift(),{content:[{id:'c1',revision:8,title:'Article'}]});await flush();
 records[2].status='sending';records.forEach(r=>r.revision=8);
 result(requests.shift(),{revision:8,binding:{appid:'current',version:3},records});await flush();
 assert(node('sync').disabled);assert(!recheck.hidden&&!recheck.disabled);assert.equal(evaluate('recoveryJob'),'blocked');
 const verifyBlocked=recheck.onclick();const chosen=requests.shift();assert(chosen.url.endsWith('/blocked/reconcile'));
 result(chosen,{id:'blocked',appid:'current',revision:8,status:'synced'});await verifyBlocked;
 console.log('PASS: tenant isolation, revision races, loading gates, receipt history, lost response recovery, no automatic resend and viewer controls');
}
main().catch(e=>{console.error(e);process.exitCode=1});
