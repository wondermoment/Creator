const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const calls=[],listeners=[];
const c={internationalResearchers:[{id:'research-only',research:true}],document:{addEventListener:(t,f)=>listeners.push(f)},openCoach:(...a)=>calls.push(a)};
vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/services.js','utf8'),c);
for(const [id,field] of [['mary-lin','营养代谢'],['zhang-zhanhui','运动体能'],['hou','家族长寿']]){
 listeners[0]({target:{closest:()=>({dataset:{expertChat:id},hasAttribute:()=>false})}});
 const [skill,prompt]=calls.at(-1);assert.equal(skill,'general-health');assert.ok(prompt.includes(field));assert.ok(prompt.includes('平台健康助手'));assert.ok(prompt.includes('不要以'));assert.ok(prompt.includes('不要把一般建议当作个体诊断'));
}
const count=calls.length;vm.runInContext("openExpertInquiry('missing');openExpertInquiry('research-only')",c);assert.equal(calls.length,count);
console.log('PASS: 3 expert entry events preserve specialty and identity limits; missing/research entries ignored. No model calls or user storage.');
