from pathlib import Path
def change(file,old,new):
 p=Path(file);s=p.read_text('utf-8');assert old in s,(file,old);p.write_text(s.replace(old,new),encoding='utf-8')
change('frontend/diet.js','/^nutrient-[0-5]$/','/^nutrient-\\d+$/')
change('frontend/nutrients.js',"['全部',...new Set(nutrientItems.map(n=>n.tag))]","['全部','肌肉与体能','骨骼健康','肠道与代谢','基础营养','前沿研究']")
change('frontend/nutrients.js','题录与摘要核对：2026-10-04。','题录与摘要核对：${esc(a.reviewedAt||\'2026-10-04\')}。')
change('frontend/nutrients.js','class="primary full" data-coach="nutrients"','class="primary full" data-coach="nutrients" data-nutrient-index="${i}"')
change('frontend/coach-chat.js',"if(b)openCoach(b.dataset.coach,b.dataset.question||'')","if(b)openCoach(b.dataset.coach,b.dataset.question||'',b.hasAttribute('data-nutrient-index')&&typeof nutrientConsultOptions==='function'?nutrientConsultOptions(Number(b.dataset.nutrientIndex)):{})")
change('frontend/index.html','nutrients.js?v=flow-7','nutrients.js?v=expanded-8')
change('frontend/index.html','diet.js?v=qiao-coaches-5','diet.js?v=nutrient-routes-6')
change('frontend/index.html','coach-chat.js?v=capabilities-6','coach-chat.js?v=nutrient-context-7')
# Activate the additions only once all 18 project assets have been reviewed and saved.
change('frontend/index.html','<script src="/static/coach-chat.js','<script src="/static/nutrient-additions.js?v=1" defer></script><script src="/static/coach-chat.js')
