// Synthetic storage and download boundary only; no existing user data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let blocked=false,changing=false,reads=0,clicked=0,removed=0,blob,failClick=false;
const entries=new Map([['wld-reading-notes','[{"excerpt":"中文旧笔记","extra":"kept"}]'],['wld-reading-note:a','{"id":"a","excerpt":"新笔记"}'],['auth-token','do-not-export'],['wld-health','private unrelated']]);
const revoked=[],timers=[],events=[];
class Url extends URL {static createObjectURL(value){blob=value;return 'blob:synthetic'}static revokeObjectURL(value){revoked.push(value)}}
const c={URL:Url,Blob,houBooks:[],esc:x=>String(x??''),window:{},setTimeout(fn,ms){assert.equal(ms,60000);timers.push(fn)},
 localStorage:{get length(){if(blocked)throw Error('denied');return entries.size},key:i=>[...entries.keys()][i],getItem(key){if(blocked)throw Error('denied');if(changing&&key==='wld-reading-note:a')return String(++reads);return entries.get(key)??null}},
 document:{addEventListener(name,fn){if(name==='click')events.push(fn)},body:{appendChild(){}},createElement(){return {click(){if(failClick)throw Error('download blocked');clicked++},remove(){removed++}}}}};
vm.createContext(c);vm.runInContext(fs.readFileSync('frontend/book-reader.js','utf8'),c);
(async()=>{
 let snapshot=c.readingBackupSnapshot();assert.equal(snapshot.version,1);assert.equal(snapshot.entries.length,2);assert.equal(snapshot.entries[0].value,entries.get(snapshot.entries[0].key));
 assert(!JSON.stringify(snapshot).includes('do-not-export'));assert(!JSON.stringify(snapshot).includes('private unrelated'));
 entries.set('wld-reading-note:a','{broken raw 中文');snapshot=c.readingBackupSnapshot();assert.equal(snapshot.entries.find(e=>e.key==='wld-reading-note:a').value,'{broken raw 中文');
 assert(c.personalKnowledgeNotes().includes('data-knowledge-export'));assert(c.personalKnowledgeNotes().includes('无法确认'));
 const before=JSON.stringify([...entries]);assert(c.downloadReadingBackup().includes('已发起下载'));
 const file=JSON.parse(await blob.text());assert.equal(file.entries.length,2);assert.equal(file.entries.find(e=>e.key==='wld-reading-note:a').value,'{broken raw 中文');
 assert.equal(JSON.stringify([...entries]),before);assert.equal(clicked,1);assert.equal(removed,1);timers.shift()();assert.equal(revoked.length,1);
 changing=true;assert.throws(()=>c.downloadReadingBackup(),/正在变化/);assert.equal(clicked,1);changing=false;
 blocked=true;assert.throws(()=>c.downloadReadingBackup(),/无法读取/);assert.equal(clicked,1);blocked=false;
 failClick=true;assert.throws(()=>c.downloadReadingBackup(),/未能发起/);assert.equal(revoked.length,2);assert.equal(removed,2);failClick=false;
 const status={textContent:''},button={disabled:false,closest:()=>({querySelector:()=>status})};
 blocked=true;events.at(-1)({target:{closest:()=>button}});assert(status.textContent.includes('无法读取'));assert(!button.disabled);blocked=false;
 entries.delete('wld-reading-note:a');entries.delete('wld-reading-notes');assert.throws(()=>c.downloadReadingBackup(),/没有可导出/);assert.equal(clicked,1);
 console.log('PASS: exact legacy/new raw strings, corrupt-data export, unrelated storage excluded, no mutation, read/consistency/download failures and URL cleanup; synthetic only.');
})().catch(e=>{console.error(e);process.exit(1)});
