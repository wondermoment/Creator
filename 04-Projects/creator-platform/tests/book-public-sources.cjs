const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ctx={URL,esc,document:{addEventListener(){}}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync('frontend/book-reader.js','utf8'),ctx);
const source={ref:'P1',document:'<script>bad</script>',text:'公开介绍',location:'非全文',url:'https://example.com/book?a=1&b=2',checked:'2026-10-06'};
assert.equal(ctx.readingSources([source]).length,1);
const html=ctx.readingReferenceHtml([source]);
assert(html.includes('查看回答时的参考资料'));assert(html.includes('rel="noopener noreferrer"'));
assert(html.includes('&lt;script&gt;'));assert(!html.includes('<script>'));assert(html.includes('&amp;b=2'));
for(const url of ['javascript:alert(1)','data:text/html,x','http://example.com','https://user:password@example.com']){
 assert.throws(()=>ctx.readingSources([{...source,url}]));
 assert(!ctx.readingReferenceHtml([{...source,url}]).includes('<a '));
}
const original={ref:'S1',location:'第2页',text:'用户原文片段'};
assert(ctx.readingReferenceHtml([original]).includes('查看回答时的原文摘录'));
assert.equal(ctx.readingReferenceHtml([]),'');
console.log('Public references: safe links, escaped text, original-source compatibility passed');
