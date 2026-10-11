from pathlib import Path
p=Path('frontend/travel-guides.js');s=p.read_text('utf-8')
old="g.sources.map(s=>esc(s.name)).join('、')"
new="g.sources.map(s=>/^https?:\\/\\//.test(s.url||'')?`<a href=\"${esc(s.url)}\" target=\"_blank\" rel=\"noopener noreferrer\">${esc(s.name)} ↗</a>`:esc(s.name)).join('、')"
assert old in s;p.write_text(s.replace(old,new),encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');s=s.replace('travel-guides.js?v=kamalaya-hd-4','travel-guides.js?v=source-links-5');p.write_text(s,encoding='utf-8')
