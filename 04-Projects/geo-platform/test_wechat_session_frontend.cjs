const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/wechat-settings.js','utf8');
const flush=()=>new Promise(r=>setImmediate(r));
async function scenario(status){
 const nodes=new Map(),requests=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',style:{},hidden:false,checked:false,disabled:false,after(){},append(){},removeAttribute(k){delete this[k]},querySelector(){return node('save')}});return nodes.get(id)};
 const ctx=vm.createContext({URLSearchParams,encodeURIComponent,location:{search:'?project=p&content=c&revision=1'},
  document:{getElementById:node,createElement:()=>node('created-'+nodes.size)},
  fetch(url,options){return new Promise(resolve=>requests.push({url,options,resolve}))}});
 const evaluate=s=>vm.runInContext(s,ctx);
 const reply=data=>requests.shift().resolve({ok:true,status:200,json:async()=>data});
 vm.runInContext(source,ctx);
 reply({csrf:'old-session',projects:[{id:'p',name:'Company',role:'owner'}]});await flush();
 reply({appid:'wxfixture',name:'Account',version:1,has_secret:true});await flush();
 reply({content:[{id:'c',revision:1,title:'Private title'}]});await flush();
 reply({revision:1,binding:{appid:'wxfixture',version:1},next_digest:'Private summary',records:[]});await flush();
 // Two old responses are in flight, one with a body not yet decoded.
 const stale=evaluate("api('/old-read').then(show).catch(()=>{})");const old=requests.shift();
 const slow=evaluate("api('/slow-read').then(show).catch(()=>{})");const bodyRequest=requests.shift();
 let finishBody;bodyRequest.resolve({ok:true,status:200,json:()=>new Promise(r=>finishBody=r)});await flush();
 node('secret').value='unsent-secret';node('confirm').checked=true;
 const send=node('sync').onclick();const rejected=requests.shift();
 assert.equal(rejected.options.method,'POST');
 rejected.resolve({ok:false,status,json:async()=>({detail:'access changed'})});await send;
 assert(evaluate('accessBlocked'));assert.equal(evaluate('me'),null);
 assert(node('binding').hidden&&node('draft').hidden&&node('sync').disabled&&node('project').disabled);
 for(const id of ['secret','appid','name','project'])assert.equal(node(id).value,'');
 assert.equal(node('article').textContent,'');assert.equal(node('receipt').textContent,'');assert(!node('confirm').checked);
 assert.equal(evaluate('digestPreview.textContent'),'');assert.equal(evaluate('targetPreview.textContent'),'');
 assert.equal(node('preview').href,undefined);
 assert.equal(requests.length,0,'no automatic reload under changed identity');
 const late={appid:'OLD',name:'private',version:1};old.resolve({ok:true,status:200,json:async()=>late});finishBody(late);
 await Promise.all([stale,slow]);
 assert.equal(evaluate('config'),null);assert.equal(node('appid').value,'');
 await node('test').onclick();await node('sync').onclick();await evaluate('load()');assert.equal(requests.length,0);
 assert(node('status').textContent.includes('已清空本页信息'));
}
(async()=>{await scenario(401);await scenario(403);console.log('PASS: expired/replaced session clears private UI, blocks recovery reads and discards late response bodies');})().catch(e=>{console.error(e);process.exitCode=1});
