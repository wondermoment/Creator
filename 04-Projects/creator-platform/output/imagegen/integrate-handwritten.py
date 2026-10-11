import sys,json,re
from pathlib import Path
from PIL import Image
recipe_id,source=sys.argv[1:3]
rows=json.loads(Path('output/imagegen/recipe-handwritten-manifest.json').read_text('utf-8'))
assert recipe_id in [x['id'] for x in rows]
source=Path(source);assert source.is_file()
Image.open(source).convert('RGB').save('frontend/assets/recipes/'+recipe_id+'-ingredients-handwritten.webp',quality=93,method=6)
p=Path('frontend/lifestyle-additions.js');s=p.read_text('utf-8');ids=json.loads(re.search(r'const recipeHandwrittenIds=(.*?);',s).group(1));ids=list(dict.fromkeys(ids+[recipe_id]));s=re.sub(r'const recipeHandwrittenIds=.*?;', 'const recipeHandwrittenIds='+json.dumps(ids)+';',s,count=1);p.write_text(s,encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');s=re.sub(r'lifestyle-additions.js\?v=handwritten-[\w-]+','lifestyle-additions.js?v=handwritten-'+str(len(ids)),s);p.write_text(s,encoding='utf-8')
p=Path('output/imagegen/handwritten-verified.json');d=json.loads(p.read_text('utf-8')) if p.exists() else {};d[recipe_id]={'source':str(source),'verified':'Visual review of title, ingredients, quantities and arrows','asset':'/static/assets/recipes/'+recipe_id+'-ingredients-handwritten.webp'};p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');print(len(ids),'of',len(rows),'integrated')
