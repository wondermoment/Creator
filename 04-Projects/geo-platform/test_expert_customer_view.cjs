const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx=vm.createContext({console,Intl,Date,URL,URLSearchParams,Map,Set,document:{querySelector(){return {addEventListener(){}}},addEventListener(){},hidden:false},window:{addEventListener(){}},location:{hash:'#skills?expert=strategist'},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},clearTimeout(){}});
for(const name of ['app','planning','knowledge','manager','leads','delivery','sample','experts'])vm.runInContext(fs.readFileSync(`static/${name}.js`,'utf8'),ctx);
const run=s=>vm.runInContext(s,ctx);
run(`pid='p';me={identity:'user',base_skills:[],can_manage_prompts:true};state={role:'owner',project:{name:'测试企业'},skill:[],content_reference:[],connector_status:[{provider:'model',model:'INTERNAL_MODEL'}],execution:[]};`);
for(const id of run('contentExperts.map(e=>e[0])')){
 ctx.expertId=id;
 run(`activeExpert=expertId;location.hash='#skills?expert='+expertId;state.execution=[{id:'normal',job_type:'expert_chat',status:'succeeded',payload:{expert_id:expertId,question:'正常业务需求',sources:[],soul_version:9,skill_name:'INTERNAL_SKILL',skill_version:8},result:{answer:'正常业务答复',model:'INTERNAL_MODEL',usage:{prompt_tokens:12345}}},{id:'qa',job_type:'expert_chat',status:'succeeded',payload:{expert_id:expertId,question:'【本机功能验收】测试记录',sources:[]},result:{answer:'TEST_ONLY'}}]`);
 const html=run('skillsPage()');
 for(const hidden of ['INTERNAL_MODEL','INTERNAL_SKILL','12345','TEST_ONLY','本机功能验收','本次 Skill','专家版本','/admin'])assert(!html.includes(hidden),`${id}: ${hidden}`);
 assert(html.includes('正常业务答复'));assert(html.includes('继续编辑图文'));assert(html.includes('name="skill_id"'));assert(!html.includes('<select name="skill_id"'));
 assert.equal(run('state.execution.length'),2,'do not delete historical records');
}
console.log('PASS: all six experts show business conversations, hide internal metadata/tests, retain configured skill submission and original records');
