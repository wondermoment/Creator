from pathlib import Path
assets=Path('frontend/assets/testing')
for stem in ['test-telomere','test-methylation','test-igg','test-ige']:
 assert (assets/(stem+'-science.webp')).is_file(),stem
p=Path('frontend/testing-catalog.js');s=p.read_text('utf-8');start=s.index('function testingArtwork(p){');end=s.index('\nfunction testingCards()',start)
s=s[:start]+"""function testingArtwork(p){const themes={'基础指标':'biomarkers','基因检测':'genetics','衰老研究':'genetics','菌群检测':'microbiome','营养评估':'nutrition','代谢评估':'metabolism','激素评估':'hormones','食物相关':'foods','健康评估':'liver','暴露评估':'environment'};const science=typeof testingScience==='undefined'?null:testingScience[p.id];const file=science?science.image:(themes[p.topic]||'biomarkers')+'.webp';return `<figure class="testing-artwork" style="margin:0;background:#f4f0f8"><img src="/static/assets/testing/${file}" alt="${esc(science?science.title+'科普图：'+science.points.map(x=>x[0]).join('、')+'；'+science.limit:p.name+'相关主题插画')}" loading="lazy" width="1254" height="1254" style="display:block;width:100%;height:auto;aspect-ratio:1;object-fit:contain"><figcaption style="padding:4px 14px 8px;font-size:11px;color:#766b84">${esc(science?'原理示意 · 非个人报告 · '+science.limit:p.topic+' · 主题示意')}</figcaption></figure>`}
"""+s[end:]
s=s.replace('<section class="lifestyle-note"><h2>预约前，帮你核对清楚', """${typeof testingScienceGuide==='function'?testingScienceGuide(p):''}<section class="lifestyle-note"><h2>预约前，帮你核对清楚""")
p.write_text(s,encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8').replace('<script src="/static/testing-catalog.js?v=full-art-2"','<script src="/static/testing-science.js?v=1" defer></script><script src="/static/testing-catalog.js?v=science-3"').replace('customer-service.js?v=clinic-context-5','customer-service.js?v=testing-science-6');p.write_text(s,encoding='utf-8')
