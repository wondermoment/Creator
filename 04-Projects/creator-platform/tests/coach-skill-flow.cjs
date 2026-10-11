// Exercises all seven actual skill definitions through chat request construction.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let nodes={},handlers=[],requests=[],html='';
const c={AbortController,document:{addEventListener:(t,f)=>handlers.push(f),getElementById:id=>nodes[id]},esc:x=>String(x),setTimeout:()=>1,clearTimeout(){},showForm(title,body){html=body;nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={value:'',disabled:false,isConnected:true,innerHTML:'',textContent:'',addEventListener(){},querySelector(){return null},focus(){this.focused=true}}},post:async(url,body)=>{requests.push({url,body});return {context_version:1,answer:'Synthetic response'}}};
vm.createContext(c);for(const f of ['skill-quality','diet','chat-format','coach-chat'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
(async()=>{
 const skills=vm.runInContext('foodSkills',c);assert.equal(skills.length,7);
 for(const skill of skills){
  c.openCoach(skill.id);const initial=requests.length;assert(html.includes('data-coach-starter='));
  const question=vm.runInContext(`coachStarters['${skill.id}'][0]`,c);
  handlers.at(-1)({target:{closest:()=>({dataset:{coachStarter:question}})}});assert.equal(nodes['coach-question'].value,question);assert.equal(requests.length,initial);
  for(let turn=0;turn<6;turn++){
   nodes['coach-question'].value='synthetic '+turn;await nodes.form.onsubmit({preventDefault(){}});
   const req=requests.at(-1);assert.equal(req.url,'/coaches/'+(skill.id==='service-matching'?'general-health':skill.id)+'/chat');
   assert(req.body.history[0].content.includes(skill.task));assert(req.body.history[0].content.includes('没有计时、保存、导出媒体、预约或购买执行工具'));assert(req.body.history.length<=10);
  }
 }
 const mindful=skills.find(s=>s.id==='rest-and-reflection');assert(mindful.task.includes('不要求深呼吸、屏息、闭眼'));assert(mindful.task.includes('不能声称已保存'));
 console.log('PASS: seven real skill routes × six turns; complete task + capability limits retained, all starter buttons fill without sending. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
