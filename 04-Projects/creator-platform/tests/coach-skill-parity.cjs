const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const context={document:{addEventListener(){}}};vm.createContext(context);
for(const name of ['skill-quality','diet'])vm.runInContext(fs.readFileSync(`frontend/${name}.js`,'utf8'),context);
const backend=JSON.parse(fs.readFileSync('backend/app/coach_knowledge.json','utf8'));
const all=vm.runInContext('foodSkills',context);
assert.equal(all.length,backend.skills.length);
for(const frontend of all){
 const runtime=backend.skills.find(s=>s.id===frontend.id);
 assert(runtime,'Missing runtime skill '+frontend.id);
 assert.equal(frontend.task,runtime.task,'Export/runtime task mismatch: '+frontend.id);
 assert(context.buildLongevitySkill(frontend).includes(runtime.task));
}
const shared=vm.runInContext('longevitySkillStandard',context).trim();
const policy=fs.readFileSync('backend/app/coach_policy.md','utf8').replace(/\r\n/g,'\n').split('## 当前能力')[0].trim();
assert.equal(shared,policy,'Exported safety/intake contract and runtime policy diverged');
const exported=context.buildLongevitySkill(all[0]);
assert(exported.includes(shared));
console.log('All seven skill export/runtime tasks and full shared policy parity passed');
