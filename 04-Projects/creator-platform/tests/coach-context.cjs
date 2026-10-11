const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={document:{addEventListener(){}}};vm.createContext(c);
vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),c);vm.runInContext(fs.readFileSync('frontend/coach-chat.js','utf8'),c);
const history=[];
for(let i=0;i<14;i++)history.push({role:'user',content:i===0?'我对花生严重过敏，正在服用华法林。':`第${i}轮合成问题`},{role:'assistant',content:`第${i}轮合成回复`});
for(const context of ['', '运动教练任务说明']){
 const body=c.coachPayload('继续',history,context);
 const combined=[...body.earlier_user_messages,...body.history.filter(h=>h.role==='user'&&h.content!==context).map(h=>h.content)];
 assert.deepEqual(Array.from(combined),history.filter(h=>h.role==='user').map(h=>h.content),'Every user turn retained once, in order');
 assert(body.history.length<=10);assert(!body.earlier_user_messages.some(t=>t.includes('回复')));
 assert.equal(history.length,28,'Building payload must not mutate conversation');
}
const huge=[];for(let i=0;i<50;i++)huge.push({role:'user',content:'合成输入'},{role:'assistant',content:'合成输出'});
assert.throws(()=>c.coachPayload('继续',huge),/上下文上限/);
const long=[];for(let i=0;i<14;i++)long.push({role:'user',content:'字'.repeat(2000)},{role:'assistant',content:'输出'});
assert.throws(()=>c.coachPayload('继续',long),/上下文上限/);
assert.equal(c.coachPayload('新会话',[]).earlier_user_messages.length,0);
// Emit real frontend request as a fixture for backend Message/prompt integration.
fs.mkdirSync('output',{recursive:true});
fs.writeFileSync('output/coach-context-request.json',JSON.stringify(c.coachPayload('宫保鸡丁能加花生吗？',history,'中餐菜谱教练'),null,2));
console.log('PASS: 14-turn user context retained in order, no duplicated/assistant facts, bounded context, fresh-session isolation.');
