from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'frontend/book-reader.js';s=p.read_text('utf-8')
old='<p class="${h.role===\'user\'?\'chat-question\':\'\'}" style="white-space:pre-wrap">${esc(h.content)}</p>'
assert old in s
s=s.replace(old,'${readingMessageHtml(h)}')
p.write_text(s,encoding='utf-8')
p=root/'frontend/index.html';s=p.read_text('utf-8').replace('book-reader.js?v=personal-entry-13','book-reader.js?v=formatted-14').replace('sunny-theme.css?v=book-help-20261005','sunny-theme.css?v=reading-format-20261006');p.write_text(s,encoding='utf-8')
