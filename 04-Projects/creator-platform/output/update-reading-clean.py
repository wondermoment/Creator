from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'frontend/book-reader.js';s=p.read_text('utf-8')
s=s.replace('<p id="reading-status" class="small muted">','<p id="reading-status" class="small muted" hidden>')
s=s.replace('${coachUrgentHelp()}<details class="reading-sources">','<details class="reading-sources">')
s=s.replace('sourceReady=!!s.ready;status.textContent=', 'sourceReady=!!s.ready;status.hidden=!s.ready&&!!s.model_ready;status.textContent=')
s=s.replace("status.textContent='原文状态加载失败：'", "status.hidden=false;status.textContent='原文状态加载失败：'")
s=s.replace("status.textContent='历史记录加载失败：'", "status.hidden=false;status.textContent='历史记录加载失败：'")
s=s.replace("status.textContent='正在检查原文与历史记录…';let loaded=false;", "status.hidden=true;status.textContent='正在检查原文与历史记录…';let loaded=false;")
s=s.replace("status.textContent='请核对上传后的原文状态';", "status.hidden=false;status.textContent='请核对上传后的原文状态';")
p.write_text(s,encoding='utf-8')
p=root/'tests/book-reader-async.cjs';s=p.read_text('utf-8')
s=s.replace("assert(h.markup.includes(h.ctx.coachUrgentHelp()));assert(h.markup.indexOf('coach-urgent-help')<h.markup.indexOf('id=\"reading-log\"'));", "assert(!h.markup.includes('coach-urgent-help'));assert(!h.markup.includes('reading-consent'));")
s=s.replace('local urgent panel present before loading and outside log','clean book header without consent/urgent panels')
p.write_text(s,encoding='utf-8')
# The three user-requested questions supersede the initial per-book starters.
p=root/'frontend/book-conversations.js';s=p.read_text('utf-8')
import re
s=re.sub(r"('(?:hou-\d+|new-[a-z-]+|zhang-[a-z-]+)':\['[^']*'),\s*'[^']*',\s*'[^']*'\]",r'\1]',s)
p.write_text(s,encoding='utf-8')
p=root/'frontend/index.html';s=p.read_text('utf-8').replace('book-conversations.js?v=1','book-conversations.js?v=2').replace('book-reader.js?v=personal-entry-12','book-reader.js?v=personal-entry-13');p.write_text(s,encoding='utf-8')
