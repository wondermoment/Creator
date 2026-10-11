const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={document:{addEventListener(){}},esc:s=>String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))};vm.createContext(c);
for(const name of ['book-metadata','books-hou','book-conversations','book-reader'])vm.runInContext(fs.readFileSync(`frontend/${name}.js`,'utf8'),c);
const books=vm.runInContext('houBooks',c),entries=vm.runInContext('bookConversations',c);
for(const book of books){
 assert(entries[book.id],book.id);
 const guide=c.readingGuide(book),html=c.readingWelcome(book);
 assert(guide.intro);assert.equal(guide.questions.length,3);assert.equal((html.match(/data-reading-prompt=/g)||[]).length,3);
 assert(html.includes('第一性原理'));assert(html.includes('最牛'));assert(html.includes('最差'));
}
assert.equal(new Set(books.map(b=>c.readingGuide(b).heading)).size,books.length);
const proof={books:books.length,distinctHeadings:books.length,startersPerBook:3,source:'existing catalogue metadata; editorial prompts, not full-text summaries',examples:['new-noma','zhang-running','new-longevity-singularity'].map(id=>({id,...c.readingGuide(books.find(b=>b.id===id))}))};
fs.writeFileSync('docs/book-entry-check-20261006.json',JSON.stringify(proof,null,2));console.log(`PASS ${books.length} distinct book headings/descriptions with the requested three questions`);
