// Synthetic DOM and deferred network: no model calls, clipboard, or user storage.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function harness(){
 let nodes={},pending=[],timers=new Map(),sequence=0;
 const c={AbortController,foodSkills:[],esc:x=>String(x),document:{addEventListener(){},getElementById:id=>nodes[id]},setTimeout:f=>{timers.set(++sequence,f);return sequence},clearTimeout:id=>timers.delete(id),showForm(){Object.values(nodes).forEach(n=>n.isConnected=false);nodes={};for(const id of ['form','coach-question','coach-log','coach-error','submit'])nodes[id]={isConnected:true,value:'',disabled:false,innerHTML:'',textContent:'',events:{},addEventListener(t,f){this.events[t]=f},querySelector(){return null}};nodes.form.requestSubmit=()=>nodes.form.onsubmit({preventDefault(){}})},post(url,body){return new Promise((resolve,reject)=>pending.push({url,body,resolve,reject}))}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),c);vm.runInContext(fs.readFileSync('frontend/coach-chat.js','utf8'),c);
 return {c,get n(){return nodes},pending,timers,send(){return nodes.form.onsubmit({preventDefault(){}})}};
}
(async()=>{
 const h=harness();h.c.openCoach('general-health');await h.send();assert.equal(h.pending.length,0);
 h.n['coach-question'].value='合成测试问题';const first=h.send();await h.send();assert.equal(h.pending.length,1);assert.equal(h.n.submit.disabled,true);
 h.pending.shift().reject(Error('离线'));await first;assert.equal(h.n['coach-question'].value,'合成测试问题');assert.equal(h.n.submit.disabled,false);assert.match(h.n['coach-error'].textContent,/问题已保留/);assert.equal(h.timers.size,0);
 const retry=h.send();const req=h.pending.shift();assert.equal(req.body.history.length,0);req.resolve({answer:'合成回复'});await retry;assert.equal(h.n['coach-question'].value,'');
 h.n['coach-question'].value='下一问';const next=h.send();const nextReq=h.pending.shift();assert.equal(nextReq.body.history.length,2);assert.equal(nextReq.body.history[1].content,'合成回复');nextReq.resolve({answer:''});await next;assert.equal(h.n['coach-question'].value,'下一问');assert.match(h.n['coach-error'].textContent,/未收到有效回复/);
 const stale=h.send();const old=h.pending.shift();h.c.openCoach('nutrients');h.n['coach-question'].value='新窗口草稿';old.resolve({answer:'旧窗口结果'});await stale;assert.equal(h.n['coach-question'].value,'新窗口草稿');assert.ok(!h.n['coach-log'].innerHTML.includes('旧窗口结果'));assert.equal(h.n.submit.disabled,false);assert.equal(h.timers.size,0);
 for(const event of [{key:'Enter',isComposing:true},{key:'Enter',keyCode:229},{key:'Enter',shiftKey:true}]){h.n['coach-question'].events.keydown({...event,preventDefault(){throw Error('IME/换行被拦截')}})}assert.equal(h.pending.length,0);
 // A permanently pending transport must release the form without losing draft,
 // adding a fake history turn, auto-retrying, or letting a late answer overwrite.
 h.n['coach-question'].value='网络挂起的合成问题';const hung=h.send();const hungReq=h.pending.shift();
 [...h.timers.values()].forEach(f=>f());await hung;
 assert.equal(h.n.submit.disabled,false);assert.equal(h.n['coach-question'].disabled,false);
 assert.equal(h.n['coach-question'].value,'网络挂起的合成问题');
 assert.match(h.n['coach-error'].textContent,/服务端可能仍在处理/);assert.equal(h.pending.length,0);assert.equal(h.timers.size,0);
 h.n['coach-question'].value='超时后修改的草稿';hungReq.resolve({answer:'迟到的旧回答'});await Promise.resolve();
 assert.equal(h.n['coach-question'].value,'超时后修改的草稿');assert.ok(!h.n['coach-log'].innerHTML.includes('迟到的旧回答'));
 const after=h.send();const afterReq=h.pending.shift();assert.equal(afterReq.body.history.length,0);afterReq.resolve({answer:'重试成功'});await after;assert.equal(h.timers.size,0);
 const long=harness();long.c.openCoach('general-health');
 for(let i=0;i<6;i++){long.n['coach-question'].value=i===0?'严重花生过敏':'合成问题'+i;const p=long.send();long.pending.shift().resolve({answer:'合成回复',context_version:1});await p;}
 long.n['coach-question'].value='下一问';const legacy=long.send(),legacyReq=long.pending.shift();
 assert.equal(legacyReq.body.earlier_user_messages[0],'严重花生过敏');
 legacyReq.resolve({answer:'旧后台未处理早期信息的回答'});await legacy;
 assert.match(long.n['coach-error'].textContent,/后台尚未启用/);assert.equal(long.n['coach-question'].value,'下一问');
 assert(!long.n['coach-log'].innerHTML.includes('旧后台未处理早期信息的回答'));assert.equal(long.n.submit.disabled,false);
 const upgraded=long.send(),newReq=long.pending.shift();assert.deepEqual(newReq.body,legacyReq.body);
 newReq.resolve({answer:'新后台回复',context_version:1});await upgraded;assert.equal(long.n['coach-question'].value,'');
 const formatted=harness();formatted.c.openCoach('general-health');
 formatted.n['coach-question'].value='合成排版问题';const formatSend=formatted.send();
 formatted.pending.shift().resolve({answer:'### 注意事项\n\n**请先核对用药。**\n\n- 保留 2 * 3 和 C#\n- <img src=x onerror=alert(1)>'});await formatSend;
 const html=formatted.n['coach-log'].innerHTML;
 assert(html.includes('<h3>注意事项</h3>'));assert(html.includes('<strong>请先核对用药。</strong>'));
 assert(html.includes('<ul>'));assert(!html.includes('<img'));assert(html.includes('&lt;img'));
 assert(!html.includes('###'));assert(!html.includes('**'));assert(html.includes('2 * 3 和 C#'));
 formatted.n['coach-question'].value='继续';const follow=formatted.send();
 assert(formatted.n['coach-log'].innerHTML.includes('<strong>请先核对用药。</strong>'),'History keeps formatting while next reply is pending');
 formatted.pending.shift().reject(Error('合成失败'));await follow;
 assert(formatted.n['coach-log'].innerHTML.includes('<strong>请先核对用药。</strong>'));
 assert.equal(formatted.n['coach-question'].value,'继续');
 console.log('PASS: draft/retry/stale-window/IME/timeout guards, context guard and safe reply formatting across success, follow-up and failure. Synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
