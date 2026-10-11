import sys,json
from pathlib import Path
from PIL import Image
id,source=sys.argv[1:3]
assert id in ['protein','fiber','calcium','b12','magnesium','creatine']
im=Image.open(source).convert('RGB');w,h=im.size
assert abs(w/h-3)<.05
for i in range(3):
 panel=im.crop((round(i*w/3),0,round((i+1)*w/3),h))
 panel.save(f'frontend/assets/nutrients/{id}-flow-{i+1}.webp',quality=94,method=6)
 if i==0:panel.save(f'frontend/assets/nutrients/{id}-science.webp',quality=94,method=6)
p=Path('output/imagegen/nutrient-expansion-verified.json');data=json.loads(p.read_text('utf-8')) if p.exists() else {}
data[id]={'source':source,'size':[w,h],'review':'Visually checked subject and Chinese labels. Simplified editorial illustration, not clinical validation. First panel reused as catalog cover.'}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(id,w,h)
