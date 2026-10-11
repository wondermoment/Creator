const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const pending=[],timers=new Map();let serial=0,renders=0;
const c={AbortController,URL,state:{page:'knowledge'},houBooks:[],localStorage:{getItem:()=>JSON.stringify([{excerpt:'本地笔记',at:'2026-10-06'}])},esc:s=>String(s??'').replaceAll('<','&lt;'),
 document:{addEventListener(){}},window:{addEventListener(){}},location:{hash:'#knowledge'},
 setTimeout(fn){timers.set(++serial,fn);return serial},clearTimeout:id=>timers.delete(id),render(){renders++},
 api(path,options){return new Promise((resolve,reject)=>pending.push({resolve,reject,signal:options.signal}))}};
vm.createContext(c);for(const f of ['chat-format','book-reader','portal'])vm.runInContext(fs.readFileSync('frontend/'+f+'.js','utf8'),c);
const row=(content='**关键结论**')=>({book:'synthetic',role:'assistant',content,sources:[],id:'s1',saved:1});
(async()=>{
 const initial=c.loadKnowledge(),first=pending.shift();assert(c.knowledgePage().includes('正在读取收藏'));
 first.reject(Error('offline'));await initial;assert(!c.knowledgePage().includes('还没有服务端收藏'));assert(c.knowledgePage().includes('不能据此判断收藏为空'));
 const success=c.loadKnowledge();pending.shift().resolve([row()]);await success;assert(c.knowledgePage().includes('<strong>关键结论</strong>'));
 for(const invalid of [null,{},[null],[{...row(),sources:{}}],[{...row(),book:'x" onclick="bad'}],[{...row(),role:'user'}],[{...row(),saved:0}]]){
  const task=c.loadKnowledge();pending.shift().resolve(invalid);await task;
  assert(c.knowledgePage().includes('<strong>关键结论</strong>'));assert(c.knowledgePage().includes('上次读取'));
 }
 const old=c.loadKnowledge(),oldRequest=pending.shift(),fresh=c.loadKnowledge(),freshRequest=pending.shift();assert(oldRequest.signal.aborted);
 freshRequest.resolve([row('新结果')]);await fresh;oldRequest.resolve([row('旧结果')]);await old;
 assert(c.knowledgePage().includes('新结果'));assert(!c.knowledgePage().includes('旧结果'));
 const hung=c.loadKnowledge(),hungRequest=pending.shift();[...timers.values()].forEach(fn=>fn());await hung;
 assert(hungRequest.signal.aborted);assert(c.knowledgePage().includes('超时'));assert(!c.knowledgePage().includes('data-knowledge-refresh disabled'));
 hungRequest.resolve([row('迟到结果')]);await Promise.resolve();assert(!c.knowledgePage().includes('迟到结果'));assert.equal(timers.size,0);
 const away=c.loadKnowledge();c.state.page='diet';const before=renders;pending.shift().resolve([]);await away;assert.equal(renders,before);
 c.state.page='knowledge';assert(c.knowledgePage().includes('还没有服务端收藏'));assert(c.knowledgePage().includes('本地笔记'));
 console.log('PASS: failure vs empty, timeout, invalid data preservation, stale refresh isolation, safe formatting, no cross-page repaint; synthetic reads only.');
})().catch(e=>{console.error(e);process.exit(1)});
