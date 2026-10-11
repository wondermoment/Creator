// Synthetic storage only: no browser profile, model call or user data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let notes=[{book:'a',excerpt:'old excerpt',note:'old note',location:'p1',at:'2026-10-01'}],form,selection=null,button=null;
const events={},records=new Map(),legacy=JSON.stringify(notes);
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const ctx={URL,houBooks:[{id:'a',title:'Synthetic book'}],esc,crypto:require('node:crypto').webcrypto,localStorage:{get length(){return records.size},key:i=>[...records.keys()][i],getItem:key=>key==='wld-reading-notes'?legacy:records.get(key)??null},travelSave:(key,value)=>{assert(key.startsWith('wld-reading-note:'));records.set(key,JSON.stringify(value));notes=ctx.readerNotes()},showForm:(...args)=>form=args,window:{getSelection:()=>selection},location:{href:'http://test/#article'},document:{title:'Test',addEventListener:(name,fn)=>(events[name]??=[]).push(fn),querySelector:()=>({textContent:'Synthetic article'}),getElementById:()=>button,createElement:()=>({style:{},remove(){button=null}}),body:{appendChild:b=>button=b}}};
ctx.navigator={locks:{request:async (name,options,callback)=>callback()}};
ctx.AbortController=AbortController;ctx.setTimeout=setTimeout;ctx.clearTimeout=clearTimeout;
(async()=>{
vm.createContext(ctx);vm.runInContext(fs.readFileSync('frontend/chat-format.js','utf8'),ctx);vm.runInContext(fs.readFileSync('frontend/book-reader.js','utf8'),ctx);
ctx.openBookInsights('a','<script>test</script>');assert.ok(form[1].includes('&lt;script&gt;'));
assert.throws(()=>form[3](new Map()),/请粘贴/);
await form[3](new Map([['excerpt',' synthetic excerpt '],['source','Synthetic source'],['note','<img onerror=test>']]));
assert.equal(notes.length,2);assert.equal(notes[0].excerpt,'synthetic excerpt');assert.equal(notes[1].excerpt,'old excerpt');
const html=ctx.personalKnowledgeNotes();assert.ok(html.includes('&lt;img onerror=test&gt;'));assert.ok(html.includes('old excerpt'));
const element={closest:s=>s==='#app'?{}:null};selection={toString:()=> 'selected evidence',anchorNode:{nodeType:1,...element}};
events.selectionchange[0]();assert.ok(button);button.onclick();assert.ok(form[1].includes('selected evidence'));assert.ok(form[1].includes('Synthetic article'));
selection={toString:()=>'',anchorNode:null};events.selectionchange[0]();assert.equal(button,null);
console.log('PASS: local excerpt save, empty rejection, existing note preservation, escaped rendering and article selection entry. No real data changed.');

const originalNotes=notes.slice(),book={id:'a',title:'Synthetic book'};
const answer={role:'assistant',content:'**重点** <script>bad</script>',sources:[{ref:'P1',document:'公开资料',location:'摘要',text:'未读全文',url:'https://example.org/source'}]};
await ctx.saveReadingLocal(book,answer,'我的问题 <img>');
assert(answer.localSaved);assert.equal(notes.length,originalNotes.length+1);assert.equal(notes[0].question,'我的问题 <img>');
assert.equal(notes[0].sources[0].url,'https://example.org/source');assert.deepEqual(notes[1],originalNotes[0]);
await ctx.saveReadingLocal(book,answer,'重复');assert.equal(notes.length,originalNotes.length+1);
const savedHtml=ctx.personalKnowledgeNotes();assert(savedHtml.includes('非原书摘录'));assert(savedHtml.includes('<strong>重点</strong>'));assert(savedHtml.includes('本次提供的参考资料'));assert(!savedHtml.includes('<script>'));assert(!savedHtml.includes('<img>'));
const goodSave=ctx.travelSave,failed={role:'assistant',content:'存储失败应保留回复',sources:[]};
ctx.travelSave=()=>{throw Error('quota')};await assert.rejects(()=>ctx.saveReadingLocal(book,failed,'q'),/quota/);assert(!failed.localSaved);assert.equal(notes.length,originalNotes.length+1);
ctx.travelSave=goodSave;await ctx.saveReadingLocal(book,failed,'q');assert(failed.localSaved);assert.equal(notes.length,originalNotes.length+2);
await assert.rejects(()=>ctx.saveReadingLocal(book,{role:'user',content:'用户问题'},'q'));
await assert.rejects(()=>ctx.saveReadingLocal(book,{role:'assistant',content:'无效来源',sources:[{ref:'P1',location:'x',text:'x',url:'javascript:alert(1)'}]},'q'));
console.log('PASS: public AI note stores question/answer/references, distinguishes from original excerpts, safe formatting, repeat-save dedupe and storage failure recovery.');

})().catch(error=>{console.error(error);process.exit(1)});
