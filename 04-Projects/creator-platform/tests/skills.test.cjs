const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
test('all seven downloadable contracts render with unique IDs and valid metadata',()=>{
 const c=vm.createContext({document:{addEventListener(){}},location:{hash:''}});
 vm.runInContext(fs.readFileSync('frontend/skill-quality.js','utf8'),c);
 vm.runInContext(fs.readFileSync('frontend/diet.js','utf8'),c);
 const skills=vm.runInContext('foodSkills.map(s=>({id:s.id,text:foodSkillText(s)}))',c);
 assert.equal(skills.length,7);assert.equal(new Set(skills.map(s=>s.id)).size,7);
 for(const s of skills){assert.match(s.id,/^[a-z-]+$/);assert.ok(s.text.startsWith('---\nname: '+s.id));assert.ok(!s.text.includes('undefined'));assert.ok(s.text.includes('待模型评估与专业复核'))}
});
test('evaluation fixtures have explicit prompts and observable acceptance criteria',()=>{
 const e=JSON.parse(fs.readFileSync('tests/skill-evaluations.json','utf8'));
 assert.equal(e.status,'executed_with_open_gaps');assert.equal(new Set(e.cases.map(c=>c.id)).size,e.cases.length);
 const review=JSON.parse(fs.readFileSync(e.latest_evidence,'utf8'));
 for(const c of e.cases)assert.ok(review.results.some(r=>r.id==='gate-'+c.id),'Missing real audit record: '+c.id);
 assert.ok(review.open_gaps.length,'Open acceptance gaps must remain visible');
 for(const c of e.cases){assert.ok(c.prompt.length>10);assert.ok(c.must.length>=2)}
});
