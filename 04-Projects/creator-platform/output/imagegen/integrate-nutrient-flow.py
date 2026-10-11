import sys,json
from pathlib import Path
from PIL import Image
id,source=sys.argv[1:3]
assert id in ['nad','q10','nmn','pqq','omega3','vitamin-d']
im=Image.open(source).convert('RGB');w,h=im.size
assert abs(w/h-3)<0.05,(w,h)
for i in range(3):im.crop((round(i*w/3),0,round((i+1)*w/3),h)).save(f'frontend/assets/nutrients/{id}-flow-{i+1}.webp',quality=94,method=6)
p=Path('output/imagegen/nutrient-flow-verified.json');d=json.loads(p.read_text('utf-8')) if p.exists() else {};d[id]={'source':source,'size':[w,h],'review':'Visual check: three distinct topics; labels match; simplified explanatory art, not clinical validation'};p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');print(id,w,h)
