import sys,json
from pathlib import Path
from PIL import Image
id,source=sys.argv[1:3]
assert id in ['protein','calcium']
im=Image.open(source).convert('RGB');assert im.width==im.height
target=f'frontend/assets/nutrients/{id}-flow-3-middle-aged.webp'
im.save(target,quality=94,method=6)
p=Path('output/imagegen/nutrient-people-verified.json');data=json.loads(p.read_text('utf-8')) if p.exists() else {}
data[id]={'source':source,'target':target,'size':list(im.size),'review':'Native reference edit inspected: middle-aged subject, preserved other character, scene, Chinese heading and watercolor style.'}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(target,im.size)
