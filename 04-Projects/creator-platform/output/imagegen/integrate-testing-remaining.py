from pathlib import Path
from PIL import Image
import hashlib,json
root=Path('C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a10c0b-fef2-7080-9a34-6ea9c1e5a2af')
pairs=[
 ('family','aed43aec-14a7-48cb-b560-8e5b98d165e3'),
 ('gut','54a22a49-8ed9-4ede-bce0-2c6ba93dbbcb'),
 ('oral','db41c680-0c61-4e8f-b827-3f4f1fc0035e'),
 ('nad','039cee79-e59c-43dc-b389-c1aea61104e8'),
 ('organic-acids','d7074e85-8be4-4258-9d79-28d8c9c3d5b8'),
 ('chronic','b4e3c3b8-4d6b-4c4b-bdb5-8d0ec3e54ff7'),
 ('male','080b7582-c08c-4563-b083-31d53108e837'),
 ('female','c974aa9a-515d-441e-bd52-72144cad2737'),
 ('immune','41e0f318-ce87-459d-9602-807c03346a30'),
 ('environment','03581e30-7c2c-412f-882f-57c1a49c9af0'),
 ('elements','6938a0b4-8f78-426c-9b73-cdbb80f70a0c')]
records=[]
for key,uid in pairs:
 source=root/f'exec-{uid}.png'
 target=Path(f'frontend/assets/testing/test-{key}-science.webp')
 with Image.open(source) as img:
  assert img.size==(1254,1254)
  img.save(target,'WEBP',quality=94,method=6)
 records.append({'id':f'test-{key}','source':source.as_posix(),'output':target.resolve().as_posix(),'size':[1254,1254],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'visual_review':'Each original inspected individually; theme and text reviewed, no medical certification.'})
Path('output/imagegen/testing-remaining-verified.json').write_text(json.dumps({'method':'Local Codex native image_gen using ChatGPT login; one original per item; only WebP conversion, no compositing','model_version':'not independently verified','prompt':'output/imagegen/testing-remaining-prompt.txt','exit_code':0,'items':records},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Saved {len(records)} independent educational images')
