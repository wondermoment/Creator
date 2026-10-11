// Synthetic stream transport; exercise the actual coach UI without user records.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function harness(){
 let nodes={},pending=[],timers=new Map(),serial=0;
 const c={AbortController,foodSkills:[],esc:x=>String(x).replace(/[<>&]/g,s=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[s])),
 document:{addEventListener(){},getElementById:id=>nodes[id]},
 setTimeout(f){timers.set(++serial,f);return serial},clearTimeout(id){timers.delete(id)},
 showForm(){Object.values(nodes).forEach(n=>n.isConnected=false);nodes={};
  for(const id of ['modal','form','coach-question','coach-log','coach-error','submit'])nodes[id]={isConnected:true,value:'',disabled:false,innerHTML:'',textContent:'',events:{},addEventListener(t,f){(this.events[t]||=[]).push(f)},removeEventListener(t,f){this.events[t]=(this.events[t]||[]).filter(x=>x!==f)}};
 },coachStreamRequest(path,body,onText,signal){return new Promise((resolve,reject)=>{signal.addEventListener("abort",()=>reject(Error("closed")),{once:true});pending.push({path,body,onText,signal,resolve,reject})})},
 post(){throw Error('Must use streaming transport')}
 };
 vm.createContext(c);for(const file of ['chat-format.js','coach-chat.js'])vm.runInContext(fs.readFileSync('frontend/'+file,'utf8'),c);
 return {c,pending,timers,get n(){return nodes},send(){return nodes.form.onsubmit({preventDefault(){}})}};
}
(async()=>{
 const closed=harness();closed.c.openCoach('general-health');closed.n['coach-question'].value='关闭测试';
 const closing=closed.send(),closingRequest=closed.pending.shift();
 closed.n.modal.events.close.forEach(f=>f());await closing;assert(closingRequest.signal.aborted);
 closingRequest.onText('关闭后的迟到文字');assert(!closed.n['coach-log'].innerHTML.includes('迟到文字'));
 assert.equal(closed.n.modal.events.close.length,0);assert.equal(closed.timers.size,0);
 const h=harness();h.c.openCoach('general-health');h.n['coach-question'].value='严重花生过敏，如何安排早餐？';
 const send=h.send();await h.send();assert.equal(h.pending.length,1);assert.equal(h.n['coach-question'].value,'');
 const r=h.pending.shift();assert.equal(r.path,'/coaches/general-health/chat');
 r.onText('**先避开花生。**\n\n<img onerror=bad>');
 assert(h.n['coach-log'].innerHTML.includes('<strong>先避开花生。</strong>'));
 assert(!h.n['coach-log'].innerHTML.includes('<img'));assert.equal(h.n.submit.disabled,true);
 assert.equal(h.n.submit.textContent,'正在回复…');assert.equal(h.timers.size,0);
 r.resolve({answer:'**先核对过敏原。**',context_version:1});await send;
 assert(!h.n['coach-log'].innerHTML.includes('data-coach-stream'));assert.equal(h.n.submit.disabled,false);
 h.n['coach-question'].value='换个早餐';const interrupted=h.send(),p=h.pending.shift();
 assert.equal(p.body.history[0].content,'严重花生过敏，如何安排早餐？');
 p.onText('不能保留的不完整建议');p.reject(Error('流中断'));await interrupted;
 assert.equal(h.n['coach-question'].value,'换个早餐');assert.equal(h.n.submit.disabled,false);
 assert(!h.n['coach-log'].innerHTML.includes('不能保留'));assert(h.n['coach-log'].innerHTML.includes('先核对过敏原'));
 const retry=h.send(),q=h.pending.shift();assert.equal(q.body.history.length,2);
 q.resolve({answer:'重试完整回复',context_version:1});await retry;
 // Stale deltas, errors and completion cannot paint the next modal.
 h.n['coach-question'].value='旧问题';const old=h.send(),o=h.pending.shift();h.c.openCoach('nutrients');
 h.n['coach-question'].value='新草稿';o.onText('旧流');o.reject(Error('旧错误'));await old;
 assert.equal(h.n['coach-question'].value,'新草稿');assert.equal(h.n['coach-error'].textContent,'');
 assert(!h.n['coach-log'].innerHTML.includes('旧流'));assert.equal(h.n.submit.disabled,false);
 // Every coach entry uses the stream, and the exercise compatibility route is retained.
 for(const id of ['weekly-menu','chinese-recipe','dining-guide','health-review','supplement-evidence','rest-and-reflection','service-matching']){
  const x=harness();x.c.foodSkills.push({id,title:id,desc:'test',task:'合成专项'});x.c.openCoach(id);
  x.n['coach-question'].value='合成问题';const promise=x.send(),request=x.pending.shift();
  assert.equal(request.path,'/coaches/'+(id==='service-matching'?'general-health':id)+'/chat');
  assert(request.body.history[0].content.includes('合成专项'));request.resolve({answer:'合成回复',context_version:1});await promise;
 }
 // Long-context capability failure also retracts provisional output.
 const long=harness();long.c.openCoach('general-health');
 for(let i=0;i<6;i++){long.n['coach-question'].value=i===0?'正在服用华法林':'合成问题'+i;const p=long.send();long.pending.shift().resolve({answer:'完整回复',context_version:1});await p}
 long.n['coach-question'].value='可以补K2吗';const p2=long.send(),r2=long.pending.shift();
 assert.equal(r2.body.earlier_user_messages[0],'正在服用华法林');r2.onText('旧后台临时文字');r2.resolve({answer:'不应采用的回答'});await p2;
 assert(!long.n['coach-log'].innerHTML.includes('不应采用'));assert(!long.n['coach-log'].innerHTML.includes('旧后台临时文字'));
 assert(long.n['coach-error'].textContent.includes('后台尚未启用'));assert.equal(long.n['coach-question'].value,'可以补K2吗');
 console.log('PASS: coach streaming, all 7 routes, partial/retry/history, safe formatting, stale-window and long-context guards');
})().catch(e=>{console.error(e);process.exit(1)});
