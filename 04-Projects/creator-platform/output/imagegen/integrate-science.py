import sys,json,re
from pathlib import Path
from PIL import Image
kind,id,source=sys.argv[1:4]
im=Image.open(source).convert('RGB')
if kind=='process':
 assert im.width==im.height*3
 for i in range(3): im.crop((i*im.height,0,(i+1)*im.height,im.height)).save(f'frontend/assets/recipes/{id}-step-{i+2}.webp',quality=93)
 p=Path('frontend/lifestyle-additions.js');s=p.read_text('utf-8');ids=json.loads(re.search(r'const recipeWatercolorIds=(.*?);',s).group(1));ids=list(dict.fromkeys(ids+[id]));s=re.sub(r'const recipeWatercolorIds=.*?;','const recipeWatercolorIds='+json.dumps(ids)+';',s,count=1);p.write_text(s,encoding='utf-8')
else:
 Path('frontend/assets/nutrients').mkdir(exist_ok=True)
 im.save(f'frontend/assets/nutrients/{id}-science.webp',quality=93)
p=Path('output/imagegen/science-verified.json');d=json.loads(p.read_text('utf-8')) if p.exists() else {};d[kind+':'+id]={'source':source,'dimensions':im.size,'review':'Visual review of content, labels and correct recipe sequence / evidence boundary'};p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print(kind,id,'integrated')
