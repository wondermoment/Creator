const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
let markup='',nodes={},calls=0,pending;
const c={AbortController,foodSkills:[],esc:String,document:{addEventListener(){},getElementById:id=>nodes[id]},setTimeout:()=>1,clearTimeout(){},showForm(title,body){markup=body;nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={value:'',isConnected:true,disabled:false,innerHTML:'',addEventListener(){},querySelector(){return null}}},post(){calls++;return new Promise(resolve=>pending=resolve)}};
vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),c);vm.runInContext(fs.readFileSync('frontend/coach-chat.js','utf8'),c);
(async()=>{
 for(const id of ['qiao','nutrients','general-health','research-learning']){
  c.openCoach(id);assert(markup.includes(c.coachUrgentHelp()));
  assert(markup.indexOf('coach-urgent-help')<markup.indexOf('id="coach-log"'));
 }
 const panel=c.coachUrgentHelp();assert(panel.includes('<details'));assert(panel.includes('<summary>'));assert(panel.includes('href="tel:120"'));
 assert(panel.includes('中国大陆'));assert(panel.includes('其他地区'));assert(panel.includes('不会替你拨号'));assert(panel.includes('不要等待聊天回复'));assert(panel.includes('立即伤害自己'));assert(!panel.includes('onclick'));assert(!panel.includes('data-coach'));assert(!panel.includes('<button'));
 assert.equal(calls,0,'opening chat/help never invokes model');
 nodes['coach-question'].value='合成普通咨询';const request=nodes.form.onsubmit({preventDefault(){}});assert.equal(calls,1);assert(nodes.submit.disabled);assert(markup.includes(panel));
 pending({answer:'合成回复'});await request;assert(markup.includes(panel));assert.equal(calls,1);
 console.log('PASS: urgent help in shared chat outside mutable log, explicit geography/action limits, no model call on opening; remains present while pending/after reply. Not symptom triage validation.');
})().catch(e=>{console.error(e);process.exit(1)});
