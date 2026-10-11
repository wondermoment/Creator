// Synthetic localStorage only; never opens the user's browser or files.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let raw=null,blocked=false,writes=0,form;const records=new Map();
const c={URL,crypto:require('node:crypto').webcrypto,houBooks:[{id:'a',title:'合成书'}],esc:x=>String(x??'').replaceAll('<','&lt;'),
 localStorage:{get length(){return records.size},key:i=>[...records.keys()][i],getItem(key){if(blocked)throw Error('denied');return key==='wld-reading-notes'?raw:records.get(key)??null}},
 travelSave(key,value){assert(key.startsWith('wld-reading-note:'));writes++;records.set(key,JSON.stringify(value))},
 showForm(...args){form=args},document:{addEventListener(){}},window:{}};
c.navigator={locks:{request:async (name,options,callback)=>callback()}};
c.AbortController=AbortController;c.setTimeout=setTimeout;c.clearTimeout=clearTimeout;
(async()=>{
vm.createContext(c);for(const file of ['chat-format','book-reader'])vm.runInContext(fs.readFileSync('frontend/'+file+'.js','utf8'),c);
assert.equal(c.readerNotes().length,0);
for(const bad of ['', '{broken', 'null', '{}', '[null]', '[{"excerpt":4}]','[{"excerpt":"x","at":5}]','[{"excerpt":"x","sources":[null]}]']){
 raw=bad;const before=raw,count=writes;
 assert.throws(()=>c.readerNotes(),/格式异常/);
 assert(c.personalKnowledgeNotes().includes('无法确认笔记是否为空'));
 c.openBookInsights('a','new');await assert.rejects(()=>form[3](new Map([['excerpt','new']])),/格式异常/);
 const answer={role:'assistant',content:'new AI reply',sources:[]};
 await assert.rejects(()=>c.saveReadingLocal({id:'a',title:'合成书'},answer,'q'),/格式异常/);
 assert(!answer.localSaved);assert.equal(raw,before);assert.equal(writes,count);
}
raw='[{"excerpt":"existing","extraField":"preserve"}]';blocked=true;
assert.throws(()=>c.readerNotes(),/无法读取/);assert(c.personalKnowledgeNotes().includes('暂停保存'));
await assert.rejects(()=>c.saveReadingLocal({id:'a',title:'合成书'},{role:'assistant',content:'new'},'q'),/无法读取/);assert.equal(writes,0);
blocked=false;c.openBookInsights('a');await form[3](new Map([['excerpt','new']]));
const saved=c.readerNotes();assert.equal(saved.length,2);assert.equal(saved[1].extraField,'preserve');
assert.equal(saved[1].excerpt,'existing');assert.equal(writes,1);
assert.equal(raw,'[{"excerpt":"existing","extraField":"preserve"}]');
for(const bad of ['null','{broken','{"id":"wrong","excerpt":"x"}','{"id":"broken","excerpt":2}']){records.set('wld-reading-note:broken',bad);await assert.rejects(()=>c.saveReadingLocal({id:'a',title:'合成书'},{role:'assistant',content:'blocked'},'q'),/格式异常/);assert.equal(records.get('wld-reading-note:broken'),bad);assert.equal(writes,1)}
records.delete('wld-reading-note:broken');
console.log('PASS: malformed/denied storage blocks manual and AI writes; no empty-state lie, raw bytes retained; valid legacy notes/unknown fields survive recovery.');

})().catch(error=>{console.error(error);process.exit(1)});
