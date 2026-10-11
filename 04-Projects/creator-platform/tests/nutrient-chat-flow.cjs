// Synthetic conversation only: no model, user records or external side effects.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let nodes={},events=[],requests=[],markup='';
const c={AbortController,foodSkills:[],esc:String,document:{addEventListener:(t,f)=>events.push(f),getElementById:id=>nodes[id]},setTimeout:()=>1,clearTimeout(){},showForm(title,body){markup=body;Object.values(nodes).forEach(n=>n.isConnected=false);nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={isConnected:true,value:'',disabled:false,innerHTML:'',textContent:'',addEventListener(){},querySelector(){return null},focus(){}}},post:async(url,body)=>{requests.push({url,body});return {context_version:1,answer:'合成回复'}}};
vm.createContext(c);for(const f of ['chat-format','nutrient-articles','nutrient-flow','nutrients','nutrient-additions','coach-chat'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
(async()=>{
 for(let i=0;i<12;i++){
  const n=vm.runInContext(`nutrientItems[${i}]`,c),a=vm.runInContext(`nutrientArticles[${i}]`,c),before=requests.length;
  const button={dataset:{coach:'nutrients',nutrientIndex:String(i)},hasAttribute:k=>k==='data-nutrient-index'};
  events.at(-2)({target:{closest:()=>button}});
  const q=c.nutrientConsultOptions(i).starters[2];assert(markup.includes(q));assert(markup.includes(a.doi));
  events.at(-1)({target:{closest:()=>({dataset:{coachStarter:q}})}});assert.equal(nodes['coach-question'].value,q);assert.equal(requests.length,before);
  for(let turn=0;turn<7;turn++){
   nodes['coach-question'].value='合成测试 '+turn;await nodes.form.onsubmit({preventDefault(){}});
   const req=requests.at(-1);assert.equal(req.url,'/coaches/nutrients/chat');assert(req.body.history.length<=10);
   const ctx=req.body.history[0].content;for(const text of [n.name,n.care,a.doi,a.study,a.limit])assert(ctx.includes(text));assert(ctx.length<=4000);
  }
 }
 console.log('PASS: 12 nutrient click routes × 7 turns; source, drug cautions and evidence limits retained beyond history cap; 36 contextual starters do not auto-send. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
