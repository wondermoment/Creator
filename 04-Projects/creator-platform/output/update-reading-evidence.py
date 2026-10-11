from pathlib import Path
p=Path('frontend/book-reader.js');s=p.read_text('utf-8')
old='history=rows;historyLoaded=true;paint()'
assert old in s;s=s.replace(old,'history=readingHistory(rows);historyLoaded=true;paint()')
old="if(!result.answer?.trim()||result.answer.includes('\\ufffd'))throw Error('未收到有效回复，请重试');history.push({role:'user',content:q},{role:'assistant',content:result.answer,sources:result.sources,id:result.id});"
assert old in s;s=s.replace(old,"const reply=readingReply(result);history.push({role:'user',content:q},reply);")
p.write_text(s,encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');assert 'book-reader.js?v=upload-wait-10' in s
p.write_text(s.replace('book-reader.js?v=upload-wait-10','book-reader.js?v=evidence-check-11'),encoding='utf-8')
