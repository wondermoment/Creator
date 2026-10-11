"""Preserve Office EMF figure previews in the eight authorized client manuscripts."""
import hashlib
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import server as s
from source_import import store_asset
from import_hetuo import ARTICLES

def run():
 cache=s.DB_PATH.parent/'emf-render';cache.mkdir(exist_ok=True)
 with s.db() as c:
  pid=c.execute('SELECT id FROM projects WHERE name=?',('和拓实业',)).fetchone()[0]
  restored=0
  for path in sorted(ARTICLES.glob('*.docx')):
   if path.name.startswith('~$'):continue
   k=next(k for k in s.items(c,pid,'knowledge') if k.get('source')==path.name)
   blocks=k['blocks'];lookup={b['location']:b for b in blocks}
   with zipfile.ZipFile(path) as z:
    rel={r.get('Id'):'word/'+r.get('Target','') for r in ET.fromstring(z.read('word/_rels/document.xml.rels')) if r.get('TargetMode')!='External'}
    body=ET.fromstring(z.read('word/document.xml')).find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
    for index,element in enumerate(body,1):
     for image in element.iter():
      if not image.tag.endswith('}imagedata'):continue
      part=rel.get(image.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'),'')
      if not part.endswith('.emf'):continue
      raw=z.read(part);digest=hashlib.sha256(raw).hexdigest();src=cache/(digest+'.emf');dest=cache/(digest+'.png')
      if not dest.exists():
       src.write_bytes(raw)
       subprocess.run(['powershell','-NoProfile','-File',str(s.ROOT/'render_emf.ps1'),'-InputFile',str(src),'-OutputFile',str(dest)],check=True,timeout=30,capture_output=True)
      aid=store_asset(vars(s),c,pid,dest.read_bytes(),path.stem+'-'+Path(part).stem+'-原图转换.png',{'document_asset':k['asset_id'],'part':part,'conversion':'EMF to PNG; no content alteration'},'图片')
      a=s.resource(c,pid,aid,'asset');a.update(collection='待发布原稿与配图',related_knowledge_ids=[k['id']],tags=['和拓实业','原稿图表']);s.put(c,pid,'asset',a,aid)
      loc=f'正文块 {index}'
      if loc not in lookup:
       b={'location':loc,'text':'','type':'paragraph','image_ids':[]};blocks.append(b);lookup[loc]=b
      b=lookup[loc]
      if aid not in b.setdefault('image_ids',[]):b['image_ids'].append(aid)
      if aid not in k['image_ids']:k['image_ids'].append(aid)
      restored+=1
   blocks.sort(key=lambda b:int(b['location'].split()[-1]));k['blocks']=blocks;s.put(c,pid,'knowledge',k,k['id'])
   item=next(x for x in s.items(c,pid,'content') if x.get('original_knowledge_id')==k['id'])
   if item['layout']['blocks']!=blocks:
    item['history'].append({'revision':item['revision'],'title':item['title'],'body':item['body'],'status':item['status'],'layout':item['layout']})
    item['layout']={**item['layout'],'blocks':blocks};item['revision']+=1;item['status']='pending';item['approved_revision']=None
    for v in item.get('platform_payloads',{}).values():v['attachment_ids']=list(dict.fromkeys(v['attachment_ids']+k['image_ids']))
    s.put(c,pid,'content',item,item['id'])
  print('Restored EMF figure occurrences:',restored)

if __name__=='__main__':run()
