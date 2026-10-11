from pathlib import Path
from PIL import Image
import json

base=Path('C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a10a73-dad8-71b2-adb7-14eae4fb768c')
mapping={
 'test-exome':('exec-35f32383-99ee-4336-a069-33509e3b4856.png','Coding-region schematic, scope limitation and Chinese labels reviewed.'),
 'test-genome':('exec-84414136-75f6-4f06-b81a-684dc8eebe6f.png','Broader scope, neutral schematic charts and consent labels reviewed; privacy lock is not a security certification.'),
 'test-alcohol':('exec-b4b7414f-b9c9-4f91-87b0-cdc4813974b6.png','Ethanol to acetaldehyde to acetate arrow direction and five unique labels reviewed; no safe dose claims.'),
 'test-mthfr':('exec-ae4d050a-c476-4a1c-a077-02c40e1a2469.png','Common variation, folate and clinical context reviewed; no individual dose or inevitable deficiency claims.')
}
records=[]
for key,(name,review) in mapping.items():
 src=base/name
 dest=Path('frontend/assets/testing')/(key+'-science.webp')
 with Image.open(src) as im:
  assert im.size==(1254,1254)
  im.convert('RGB').save(dest,'WEBP',quality=94,method=6)
  records.append(dict(id=key,original=str(src),file=str(dest),size=list(im.size),review=review))
Path('output/imagegen/testing-genetics-verified.json').write_text(json.dumps(dict(method='Native image_gen via ChatGPT login, four independent calls; format conversion only, no cropping/compositing',modelVersion='Not verified',prompt='output/imagegen/testing-genetics-prompt.txt',images=records),ensure_ascii=False,indent=2),encoding='utf-8')
p=Path('frontend/testing-science.js')
s=p.read_text('utf-8')
assert 'const sequencingSource=' not in s,'Already integrated; do not rerun'
p.write_text(s+'\n'+Path('output/imagegen/testing-genetics-data.js').read_text('utf-8'),encoding='utf-8')
p=Path('frontend/index.html')
s=p.read_text('utf-8')
assert 'testing-science.js?v=1' in s
p.write_text(s.replace('testing-science.js?v=1','testing-science.js?v=genetics-2'),encoding='utf-8')
print('Integrated four reviewed 1254px images and source-grounded lessons.')
