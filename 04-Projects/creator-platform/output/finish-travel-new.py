from pathlib import Path
import json
from PIL import Image
assets=json.loads(Path('output/travel-new-image-bundles-20261005.json').read_text('utf-8'))
records=[]
for key,item in zip(['rugao','tengchong','pingtan'],assets):
 out=Path(f'frontend/assets/travel/{key}-official.webp');out.parent.mkdir(parents=True,exist_ok=True)
 with Image.open(item['path']) as im:
  im.thumbnail((1600,1600));im.convert('RGB').save(out,'WEBP',quality=90)
 records.append({'destination':key,'original_url':item['url'],'output':out.as_posix(),'rights':'Public-source attribution only; commercial permission not confirmed'})
Path('output/travel-new-image-sources-20261005.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');needle='<script src="/static/recipe-expansion.js'
assert needle in s
if 'travel-new-destinations.js' not in s:s=s.replace(needle,'<script src="/static/travel-new-destinations.js?v=domestic-5-1" defer></script>'+needle)
s=s.replace('travel.js?v=back-top-4','travel.js?v=domestic-empty-5');p.write_text(s,encoding='utf-8')
p=Path('frontend/travel.js');s=p.read_text('utf-8')
old="list.map(travelCard).join('')||'<div class=\"travel-empty\">♡<h3>把向往的地方留在这里</h3><p>点击攻略图片上的爱心，就能加入收藏。</p><button class=\"secondary\" data-travel-filter=\"全部\">去发现目的地</button></div>'"
new="list.map(travelCard).join('')||travelEmpty()"
assert old in s;s=s.replace(old,new)
s+='\nfunction travelEmpty(){return travelFilter===\'收藏\'?\'<div class="travel-empty">♡<h3>把向往的地方留在这里</h3><p>点击攻略图片上的爱心，就能加入收藏。</p><button class="secondary" data-travel-filter="全部">去发现目的地</button></div>\':\'<div class="travel-empty"><h3>这个分类暂时没有攻略</h3><p>可以先看看其他目的地，或切换国内、海外。</p><button class="secondary" data-travel-filter="全部">查看其他目的地</button></div>\'}\n'
p.write_text(s,encoding='utf-8')
print('Integrated five new guides, three attributed photographs, and category-specific empty state')
