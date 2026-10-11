from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'frontend/book-reader.js';s=p.read_text('utf-8')
s=s.replace('<label class="care-check"><input type="checkbox" id="reading-consent">允许将问题、相关历史记忆和原文片段发送至本机 Codex 使用的云端模型</label>','')
s=s.replace(",consent=document.getElementById('reading-consent')",'')
s=s.replace("if(!consent.checked){error.textContent='请先确认将相关内容发送给 AI 服务';return}",'')
start=s.index("'<div class=\"reading-welcome\"><span")
end=s.index(';log.scrollTop=log.scrollHeight}paint()',start)
s=s[:start]+"readingWelcome(book)"+s[end:]
pos=s.index('async function openReadingChat(id)')
s=s[:pos]+'''function readingWelcome(book){
 const guide=typeof readingGuide==='function'?readingGuide(book):{heading:`一起聊聊《${book.title}》`,intro:'从你感兴趣的问题开始，也可以粘贴摘录一起读。',questions:[`《${book.title}》主要围绕哪些话题？`]};
 return `<div class="reading-welcome"><span class="eyebrow">${esc(book.category||'阅读交流')}</span><h2>${esc(guide.heading)}</h2><p>${esc(guide.intro)}</p><div class="reading-starters">${guide.questions.map(q=>`<button type="button" data-reading-prompt="${esc(q)}">${esc(q)}</button>`).join('')}</div></div>`;
}
'''+s[pos:]
s=s.replace("book:book.title,author:","book:book.title,editorialTopic:typeof readingGuide==='function'?readingGuide(book).intro:'',author:")
p.write_text(s,encoding='utf-8')
p=root/'frontend/index.html';s=p.read_text('utf-8').replace('<script src="/static/book-reader.js?v=evidence-check-11" defer></script>','<script src="/static/book-conversations.js?v=1" defer></script><script src="/static/book-reader.js?v=personal-entry-12" defer></script>');p.write_text(s,encoding='utf-8')
for name in ['book-reader-async','book-upload-async']:
 p=root/f'tests/{name}.cjs';s=p.read_text('utf-8').replace("'reading-consent',",'')
 s=s.replace("t.nodes['reading-question'].value='synthetic timeout';t.nodes['reading-consent'].checked=false;await t.nodes['reading-send'].onclick();assert.equal(t.pending.length,0);", "t.nodes['reading-question'].value='synthetic timeout';assert(!t.markup.includes('reading-consent'));")
 s=s.replace("t.nodes['reading-consent'].checked=true;",'').replace('consent/duplicate guards','direct-send/duplicate guards')
 p.write_text(s,encoding='utf-8')
