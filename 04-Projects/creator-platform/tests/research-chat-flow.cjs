// Exercise real researcher click handlers through the real chat form to the request boundary.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let nodes={},events=[],requests=[];
const c={AbortController,foodSkills:[],esc:x=>String(x),document:{addEventListener:(type,fn)=>events.push(fn),getElementById:id=>nodes[id]},setTimeout:()=>1,clearTimeout(){},showForm(){Object.values(nodes).forEach(n=>n.isConnected=false);nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={isConnected:true,value:'',disabled:false,innerHTML:'',textContent:'',addEventListener(){},querySelector(){return null}};},post:async(url,body)=>{requests.push({url,body});return{context_version:1,answer:'合成回复，仅用于验证请求传递。'}}};
vm.createContext(c);for(const f of ['chat-format','coach-chat','researcher-knowledge','research-experts'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
(async()=>{
 const ids=vm.runInContext('internationalResearchers.map(p=>p.id)',c);assert.equal(new Set(ids).size,4);
 for(const id of ids){
  events[2]({target:{closest:()=>({dataset:{researchExpert:id}})}});assert.equal(requests.length,ids.indexOf(id)*6,'opening does not auto-send');
  for(let turn=0;turn<6;turn++){
   nodes['coach-question'].value='合成测试第'+turn+'问';await nodes.form.onsubmit({preventDefault(){}});
   const req=requests.at(-1);assert.equal(req.url,'/coaches/research-learning/chat');assert(req.body.history.length<=10);
   const ctx=req.body.history[0].content;const p=vm.runInContext('internationalResearchers.find(p=>p.id==="'+id+'")',c);
   assert(ctx.includes(p.name));assert(ctx.includes(p.source));assert(ctx.includes('未获其授权'));assert(ctx.includes(p.boundary));assert(ctx.includes('急症'));assert(ctx.length<4000);const knowledge=vm.runInContext('researcherKnowledge["'+id+'"]',c);assert(ctx.includes(knowledge.method));for(const source of knowledge.sources){assert(ctx.includes(source.url));assert(ctx.includes(source.summary));}
   assert(req.body.history.every(h=>['user','assistant'].includes(h.role)));assert(req.body.history.every(h=>h.content.length<=4000));
  }
 }
 const count=requests.length;events[2]({target:{closest:()=>({dataset:{researchExpert:'missing'}})}});assert.equal(requests.length,count);
 console.log('PASS: four researcher click routes, six turns each; context retained after history limit, identity/contraindication/emergency boundaries and no automatic sends. Network mocked.');
})().catch(e=>{console.error(e);process.exit(1)});
