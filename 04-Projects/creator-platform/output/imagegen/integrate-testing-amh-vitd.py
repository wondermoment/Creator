from pathlib import Path
from PIL import Image
import json
base=Path('C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a10ab3-a0fc-76b3-8da7-43a714a12995')
mapping={'test-amh':('exec-1787b518-01cf-4d2d-ba20-a8bdf0cf793f.png','Follicular cells, neutral report and pregnancy-prediction limitation reviewed; simplified anatomy, not personal counts.'),'test-vitd':('exec-131dacbe-11a7-4aea-9760-baae2e689f60.png','25(OH)D label, health background and not-higher-is-better footer reviewed; no dose or universal screening claims.')}
records=[]
for key,(filename,review) in mapping.items():
 src=base/filename;dest=Path('frontend/assets/testing')/(key+'-science.webp')
 with Image.open(src) as im:
  assert im.size==(1254,1254)
  im.convert('RGB').save(dest,'WEBP',quality=94,method=6)
  records.append(dict(id=key,original=str(src),file=str(dest),size=list(im.size),review=review))
Path('output/imagegen/testing-amh-vitd-verified.json').write_text(json.dumps(dict(method='Native image_gen through ChatGPT login, two independent calls; format conversion only, no compositing',modelVersion='Not verified',prompt='output/imagegen/testing-amh-vitd-prompt.txt',images=records),ensure_ascii=False,indent=2),encoding='utf-8')
p=Path('frontend/testing-science.js');s=p.read_text('utf-8');assert "'test-amh':" not in s
p.write_text(s+'\n'+Path('output/imagegen/testing-amh-vitd-data.js').read_text('utf-8'),encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');assert 'testing-science.js?v=genetics-2' in s and 'customer-service.js?v=testing-science-6' in s
p.write_text(s.replace('testing-science.js?v=genetics-2','testing-science.js?v=amh-vitd-3').replace('customer-service.js?v=testing-science-6','customer-service.js?v=testing-sources-7'),encoding='utf-8')
print('Integrated AMH and vitamin D images, lessons and consultation source/starter versions.')
