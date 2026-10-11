const fs=require('fs'),vm=require('vm'),assert=require('assert');
const requests=[],nodes=new Map(),created=[];
const make=()=>({value:'',textContent:'',disabled:false,hidden:false,checked:false,style:{},after(){},append(){},removeAttribute(){},querySelector(){return node('save')}});
const node=id=>{if(!nodes.has(id))nodes.set(id,make());return nodes.get(id)};
const ctx=vm.createContext({URLSearchParams,encodeURIComponent,location:{search:'?project=p&content=c&revision=1'},document:{getElementById:node,createElement(){const x=make();created.push(x);return x}},fetch(url,options){return new Promise(resolve=>requests.push({url,options,resolve}))}});
const flush=()=>new Promise(r=>setImmediate(r));
const reply=data=>requests.shift().resolve({status:200,ok:true,json:async()=>data});
const cfg={appid:'wxfixture',name:'Brand',version:3,has_secret:true};
const receipt={id:'job',appid:cfg.appid,media_id:'remote',status:'synced',revision:1};
const state={content:[{id:'c',revision:1,title:'Article'}]};
const result={revision:1,binding:cfg,records:[receipt]};
async function main(){
 vm.runInContext(fs.readFileSync('static/wechat-settings.js','utf8'),ctx);
 reply({csrf:'session',projects:[{id:'p',role:'owner'}]});await flush();reply(cfg);await flush();reply(state);await flush();reply(result);await flush();
 const button=created.find(x=>x.textContent==='读取微信排版并设为后续默认模板');assert(!button.disabled);
 const task=button.onclick();assert(button.disabled);assert.equal(requests[0].url,'/api/projects/p/contents/c/wechat-draft/job/import-layout');
 assert.deepEqual(JSON.parse(requests[0].options.body),{revision:1,appid:cfg.appid,binding_version:3,make_default:true});
 await button.onclick();assert.equal(requests.length,1);
 reply({image_count:20,warnings:[]});await flush();reply(cfg);await flush();reply(state);await flush();
 reply({...result,template:{version:2,name:'Brand template'},imported_snapshot:true});await task;
 assert(node('sync').disabled);assert(node('status').textContent.includes('20 张图片'));
 node('confirm').checked=true;await node('sync').onclick();assert.equal(requests.length,0,'do not create duplicate source draft');
 const load=vm.runInContext('load()',ctx);reply(cfg);await flush();reply(state);await flush();reply({...result,records:[],template:{version:2,name:'Brand template'}});await load;
 node('confirm').checked=true;const send=node('sync').onclick();assert.equal(JSON.parse(requests[0].options.body).template_version,2);
 reply(receipt);await send;
 console.log('PASS: explicit template import targets correct receipt, blocks duplicate click/source resync and confirms exact template version');
}
main().catch(e=>{console.error(e);process.exitCode=1});
