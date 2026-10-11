'use strict';
let identity,config,executionJobs=[],loadTicket=0;
const node=id=>document.getElementById(id),message=t=>node('admin-status').textContent=t;
const wechatLink=document.createElement('a');wechatLink.href='/wechat-settings';wechatLink.textContent='公众号绑定与草稿';const wechatEntry=document.createElement('p');wechatEntry.append(wechatLink);document.querySelector('h1').after(wechatEntry);
async function request(path,method='GET',body){const r=await fetch(path,{method,headers:{'Content-Type':'application/json','x-csrf-token':identity?.csrf||''},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.detail||'请求失败');return d;}
function options(id,items,key){node(id).replaceChildren(...items.map(x=>{const o=document.createElement('option');o.value=x[key];o.textContent=x.name;return o;}));}
function showSoul(){const a=config.agents.find(x=>x.agent_id===node('admin-agent').value);node('soul-text').value=a.markdown;showExecutions();}
function showSkill(){const s=config.skills.find(x=>(x.base_id||x.id)===node('admin-skill').value);node('skill-name').value=s.name;node('skill-text').value=s.prompt;}
function showExecutions(){
 const host=node('admin-execution');host.replaceChildren();
 const rows=executionJobs.filter(j=>j.job_type==='expert_chat'&&j.payload?.expert_id===node('admin-agent').value);
 if(!rows.length){host.textContent='当前专家暂无执行记录';return;}
 for(const job of rows){const section=document.createElement('details'),summary=document.createElement('summary'),meta=document.createElement('p'),body=document.createElement('pre');
 summary.textContent=(job.payload.question||'专家对话')+' · '+job.status;
 meta.textContent=[job.result?.model||'模型未返回','专家版本 '+job.payload.soul_version,(job.payload.skill_name||'Skill')+' v'+job.payload.skill_version,(job.result?.usage?.prompt_tokens??'未知')+' 输入 / '+(job.result?.usage?.completion_tokens??'未知')+' 输出 token'].join(' · ');
 body.textContent=job.result?.answer||job.result?.reason||job.error||'尚无回复';body.style.whiteSpace='pre-wrap';section.append(summary,meta,body);host.append(section);}
}
async function load(){const pid=node('admin-project').value,ticket=++loadTicket;node('admin-execution').textContent='正在读取…';const [next,execution]=await Promise.all([request('/api/projects/'+pid+'/admin-config'),request('/api/projects/'+pid+'/execution')]);if(ticket!==loadTicket||pid!==node('admin-project').value)return;config=next;executionJobs=execution.jobs||[];options('admin-agent',config.agents,'agent_id');options('admin-skill',config.skills.map(s=>({...s,key:s.base_id||s.id})),'key');showSoul();showSkill();}
node('admin-project').onchange=()=>load().catch(e=>message(e.message));node('admin-agent').onchange=showSoul;node('admin-skill').onchange=showSkill;
for(const type of ['soul','skill'])node(type+'-form').onsubmit=async e=>{e.preventDefault();const b=e.target.querySelector('button');b.disabled=true;try{const pid=node('admin-project').value;if(type==='soul'){const a=config.agents.find(x=>x.agent_id===node('admin-agent').value);await request('/api/projects/'+pid+'/agents/'+a.agent_id+'/soul','PUT',{markdown:node('soul-text').value,version:a.version});}else{await request('/api/projects/'+pid+'/skills','POST',{base_id:node('admin-skill').value,name:node('skill-name').value,prompt:node('skill-text').value});}await load();message('新版本已保存，下次执行使用新配置；历史快照保留。');}catch(ex){message(ex.message);}finally{b.disabled=false;}};
(async()=>{try{identity=await request('/api/me');if(!identity.can_manage_prompts)throw Error('当前账号没有技术后台授权。请使用已授权的技术或管理员账号登录。');options('admin-project',identity.projects,'id');await load();node('admin-content').hidden=false;message('技术权限验证通过');}catch(e){message(e.message);}})();
