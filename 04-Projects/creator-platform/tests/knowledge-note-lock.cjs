// Two synthetic browser contexts share fake storage and a queued LockManager.
// No user data or real browser profiles are accessed.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let raw=JSON.stringify([{excerpt:'legacy',extra:'preserved'}]),writes=0,denied=false;
const queue=[],records=new Map();
const locks={request(name,options,callback){
 assert.equal(name,'wld-reading-notes-write');assert.equal(options.mode,'exclusive');
 return new Promise((resolve,reject)=>{
  const job={callback,resolve,reject,signal:options.signal};
  job.abort=()=>{queue.splice(queue.indexOf(job),1);reject(Error('aborted'))};
  options.signal.addEventListener('abort',job.abort,{once:true});queue.push(job);
 });
}};
function release(){const job=queue.shift();job.signal.removeEventListener('abort',job.abort);try{job.resolve(job.callback())}catch(e){job.reject(e)}}
function tab(){
 let form,seq=0;const timers=new Map();
 const c={URL,AbortController,navigator:{locks},crypto:require('node:crypto').webcrypto,houBooks:[{id:'a',title:'合成书'}],
  document:{addEventListener(){}},window:{},esc:x=>String(x??''),showForm(...args){form=args},
  setTimeout(fn,ms){assert.equal(ms,5000);timers.set(++seq,fn);return seq},clearTimeout:id=>timers.delete(id),
  localStorage:{get length(){return records.size},key:i=>[...records.keys()][i],getItem:key=>key==='wld-reading-notes'?raw:records.get(key)??null},travelSave(key,value){assert(key.startsWith('wld-reading-note:'));if(denied)throw Error('quota');writes++;records.set(key,JSON.stringify(value))}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/book-reader.js','utf8'),c);
 return {c,timers,get form(){return form}};
}
(async()=>{
 const a=tab(),b=tab(),book={id:'a',title:'合成书'};
 a.c.openBookInsights('a');const manual=a.form[3](new Map([['excerpt','first tab']]));
 const row={role:'assistant',content:'second tab',sources:[]};const ai=b.c.saveReadingLocal(book,row,'q');
 assert.equal(queue.length,2);assert.equal(writes,0);assert(!row.localSaved);
 release();await manual;release();await ai;
 assert.equal(a.c.readerNotes().length,3);assert.equal(a.c.readerNotes()[2].extra,'preserved');assert(row.localSaved);
 // Repeated clicks for the same answer use the same id inside the lock.
 const duplicate={role:'assistant',content:'once'};
 const d1=a.c.saveReadingLocal(book,duplicate,'q'),d2=a.c.saveReadingLocal(book,duplicate,'q');
 release();await d1;release();await d2;
 assert.equal(a.c.readerNotes().filter(n=>n.excerpt==='once').length,1);
 // Timeout removes pending work; no late write and no success marker.
 const late={role:'assistant',content:'must not write'},before=raw,count=writes;
 const wait=b.c.saveReadingLocal(book,late,'q'),rejected=assert.rejects(wait,/超时且未写入/);
 [...b.timers.values()].forEach(fn=>fn());await rejected;assert.equal(queue.length,0);assert.equal(raw,before);assert(!late.localSaved);assert.equal(writes,count);
 // Re-read at lock acquisition, catching damage introduced while waiting.
 const damage=a.c.saveReadingLocal(book,{role:'assistant',content:'blocked'},'q');raw='{broken';
 release();await assert.rejects(damage,/格式异常/);assert.equal(raw,'{broken');raw=before;
 // Quota errors release the lock; retry preserves existing data.
 const retry={role:'assistant',content:'retry'};denied=true;
 const failed=a.c.saveReadingLocal(book,retry,'q');release();await assert.rejects(failed,/quota/);assert(!retry.localSaved);
 denied=false;const recovered=b.c.saveReadingLocal(book,retry,'q');release();await recovered;assert(retry.localSaved);
 // Legacy manual entry also participates in the lock.
 a.c.openBookNotes('a');const legacy=a.form[3](new Map([['location','p1'],['note','legacy entry'],['excerpt','']]));
 assert.equal(queue.length,1);release();await legacy;assert.equal(a.c.readerNotes()[0].note,'legacy entry');
 // Never fall back to an unsafe read-modify-write if Web Locks is unavailable.
 delete b.c.navigator.locks;const unchanged=raw;
 await assert.rejects(b.c.saveReadingLocal(book,{role:'assistant',content:'unsupported'},'q'),/无法安全协调/);
 assert.equal(raw,unchanged);assert.equal(a.timers.size,0);assert.equal(b.timers.size,0);
 console.log('PASS: two-context queued saves preserve all notes, same-answer dedupe, bounded lock wait, no late writes, latest-data validation, quota recovery, all three writers and fail-closed unsupported browsers. Synthetic LockManager only.');
})().catch(e=>{console.error(e);process.exit(1)});
