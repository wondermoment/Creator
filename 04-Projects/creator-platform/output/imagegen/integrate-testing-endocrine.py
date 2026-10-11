from pathlib import Path
from PIL import Image
import json
base=Path('C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a10b89-de2c-75e0-985a-291c3d72fd0c')
mapping={'test-stress':('exec-e866056a-1af9-4a66-885c-7361a41e0afd.png','Chinese text and cortisol-example subtitle reviewed; conceptual curve not measured or normative; footer adds harmless full stop.'),'test-estrogen':('exec-00666b5d-3127-4b75-9918-a42adda95de9.png','E1/E2/E3, physiological context and no self-adjusted hormones footer reviewed; no metabolite chain or dosage.')}
records=[]
for key,(filename,review) in mapping.items():
 src=base/filename;dest=Path('frontend/assets/testing')/(key+'-science.webp')
 with Image.open(src) as im:
  assert im.size==(1254,1254)
  im.convert('RGB').save(dest,'WEBP',quality=94,method=6)
  records.append(dict(id=key,original=str(src),file=str(dest),size=list(im.size),review=review))
Path('output/imagegen/testing-endocrine-verified.json').write_text(json.dumps(dict(method='Native image_gen through ChatGPT login, two independent calls; format conversion only, no compositing',modelVersion='Not verified',prompt='output/imagegen/testing-endocrine-prompt.txt',images=records),ensure_ascii=False,indent=2),encoding='utf-8')
p=Path('frontend/testing-science.js');s=p.read_text('utf-8');assert "'test-stress':" not in s
p.write_text(s+'\n'+Path('output/imagegen/testing-endocrine-data.js').read_text('utf-8'),encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');assert 'testing-science.js?v=amh-vitd-3' in s
p.write_text(s.replace('testing-science.js?v=amh-vitd-3','testing-science.js?v=endocrine-4'),encoding='utf-8')
print('Integrated two endocrine illustrations, explanations and source boundaries.')
