// Synthetic transport/DOM only; does not test model medical competence.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let nodes={},events=[],requests=[],markup='';
const c={AbortController,foodSkills:[],esc:String,window:{addEventListener(){}},document:{addEventListener:(t,f)=>events.push(f),getElementById:id=>nodes[id]},setTimeout:()=>1,clearTimeout(){},showForm(title,body){markup=body;Object.values(nodes).forEach(n=>n.isConnected=false);nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={isConnected:true,value:'',disabled:false,innerHTML:'',textContent:'',addEventListener(){},querySelector(){return null},focus(){}}},post:async(url,body)=>{requests.push({url,body});return {context_version:1,answer:'合成回复'}}};
vm.createContext(c);
for(const f of ['chat-format','testing-science','testing-catalog','customer-service','coach-chat'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
(async()=>{
 const items=vm.runInContext('testingItems',c),lessons=vm.runInContext('testingScience',c);
 for(const item of items){
  const before=requests.length,lesson=lessons[item.id];
  c.openServiceChat(item.name+'预约咨询');
  assert.equal(requests.length,before,'opening must not send');
  if(lesson?.source){assert(markup.includes(lesson.source.url));assert(markup.includes('非实时检索'))}
  for(const starter of lesson?.starters||[]){
   assert(markup.includes(starter));
   events.at(-1)({target:{closest:()=>({dataset:{coachStarter:starter}})}});
   assert.equal(nodes['coach-question'].value,starter);assert.equal(requests.length,before,'starter must only fill draft');
  }
  for(let turn=0;turn<7;turn++){
   nodes['coach-question'].value='合成测试 '+turn;await nodes.form.onsubmit({preventDefault(){}});
   const req=requests.at(-1);assert.equal(req.url,'/coaches/qiao/chat');assert(req.body.history.length<=10);
   const ctx=req.body.history[0].content;assert(ctx.length<=4000);assert(ctx.includes(item.name));assert(ctx.includes(item.note));
   assert(ctx.includes('不得报原价'));assert(ctx.includes('没有办理订单'));assert(ctx.includes('急症先建议就近急救'));
   if(lesson){for(const point of lesson.points)assert(ctx.includes(point[1]));assert(ctx.includes(lesson.limit));if(lesson.source)assert(ctx.includes(lesson.source.url))}
  }
 }
 // Moving to a different service must not retain the previous test's questions/sources.
 c.openServiceChat('未匹配的合成商品');assert(!markup.includes('medlineplus.gov'));assert(!markup.includes('25(OH)D偏低'));
 console.log('PASS: 25 testing consultations x 7 turns retain reference/limitations/pricing/urgency context across history limit; sources visible, starters draft-only, no stale topic carryover. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
