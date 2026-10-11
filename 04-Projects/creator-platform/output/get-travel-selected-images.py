from pathlib import Path
import json,urllib.request,io
from PIL import Image
sources={s['id']:s for s in json.loads(Path('output/travel-research-20261005.json').read_text('utf-8'))}
chosen=[('pingtan',0),('tengchong',6),('rugao',11)]
manifest=[]
for key,index in chosen:
 item=sources[key]['images'][index]
 with urllib.request.urlopen(item['src'],timeout=30) as r:data=r.read()
 im=Image.open(io.BytesIO(data));im.thumbnail((1600,1600))
 out=Path(f'frontend/assets/travel/{key}-official.webp');out.parent.mkdir(parents=True,exist_ok=True);im.convert('RGB').save(out,'WEBP',quality=90)
 manifest.append({'id':key,'source_page':sources[key]['url'],'source_image':item['src'],'output':out.as_posix(),'rights':'Public official source, attribution retained; commercial permission not confirmed','size':im.size})
Path('output/travel-new-image-sources-20261005.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False))
