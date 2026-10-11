const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/wechat-settings.js','utf8');
const flush=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const nodes=new Map(),requests=[],events={};
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',style:{},hidden:false,checked:false,disabled:false,after(){},append(){},removeAttribute(k){delete this[k]},querySelector(){return node('save')}});return nodes.get(id)};
 const document={visibilityState:'visible',getElementById:node,createElement:()=>node('created-'+nodes.size),addEventListener:(type,fn)=>events[type]=fn};
 const ctx=vm.createContext({URLSearchParams,encodeURIComponent,location:{search:'?project=p&content=c&revision=1'},document,
  window:{addEventListener:(type,fn)=>events[type]=fn},fetch(url,options){return new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))}});
 const evaluate=s=>vm.runInContext(s,ctx);
 const identity={identity:'fixture',csrf:'original-session',projects:[{id:'p',name:'Company',role:'owner'}]};
 const reply=data=>requests.shift().resolve({ok:true,status:200,json:async()=>data});
 vm.runInContext(source,ctx);
 reply(identity);await flush();reply({appid:'wxfixture',name:'Account',version:1,has_secret:true});await flush();
 reply({content:[{id:'c',revision:1,title:'Article'}]});await flush();
 reply({revision:1,binding:{appid:'wxfixture',version:1},next_digest:'summary',records:[]});await flush();
 return {node,requests,events,document,evaluate,identity,reply};
}
async function main(){
 const s=await setup();s.node('confirm').checked=true;s.node('secret').value='unsent';
 s.document.visibilityState='hidden';s.events.visibilitychange();
 assert(!s.node('confirm').checked);assert.equal(s.node('secret').value,'');assert(s.node('sync').disabled);
 await s.node('sync').onclick();assert.equal(s.requests.length,0);
 s.document.visibilityState='visible';s.events.visibilitychange();s.events.focus();
 assert.equal(s.requests.length,1,'focus and visibility deduplicate check');assert.equal(s.requests[0].url,'/api/me');
 await s.node('test').onclick();assert.equal(s.requests.length,1,'no write during check');
 s.requests.shift().reject(Error('offline'));await flush();
 assert(s.node('save').disabled&&s.node('sync').disabled);assert(s.node('status').textContent.includes('暂时无法核验'));
 s.events.focus();s.reply(s.identity);await flush();assert(!s.node('save').disabled);assert(!s.node('confirm').checked);
 assert.equal(s.requests.length,0,'verification only reads session, never creates drafts');
 for(const change of ['session','role','expired']){
  const x=await setup();x.events.pageshow({persisted:true});assert(x.node('sync').disabled);
  if(change==='expired')x.requests.shift().resolve({ok:false,status:401,json:async()=>({})});
  else x.reply({...x.identity,...(change==='session'?{csrf:'new-session'}:{projects:[{id:'p',role:'viewer'}]})});
  await flush();assert(x.evaluate('accessBlocked'));assert.equal(x.node('article').textContent,'');assert(x.node('binding').hidden);
  await x.node('sync').onclick();assert.equal(x.requests.length,0);
 }
 console.log('PASS: focus/BFCache session checks deduplicate, block writes offline, reset confirmation, and clear changed identities/roles');
}
main().catch(e=>{console.error(e);process.exitCode=1});
