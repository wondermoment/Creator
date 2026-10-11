"""Bounded, local Office/text ingestion. Source material is never executed."""
import hashlib
import io
import posixpath
import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

MIMES = {'.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.md':'text/markdown', '.txt':'text/plain', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp'}

def xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('不支持包含外部实体的文档')
    return ET.fromstring(raw)

def parse(raw, suffix):
    if len(raw) > 100 * 1024 * 1024: raise ValueError('文档超过 100 MB')
    if suffix in ('.md', '.txt'):
        body = raw.decode('utf-8-sig')
        return {'body':body, 'blocks':[{'location':'全文', 'text':body}], 'images':[]}
    if suffix not in ('.docx','.pptx','.xlsx'): raise ValueError('不支持此文档格式')
    blocks, images = [], []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries = z.infolist()
        if len(entries)>5000 or sum(i.file_size for i in entries)>300*1024*1024: raise ValueError('文档解压规模超限')
        for i in entries:
            if '..' in PurePosixPath(i.filename).parts or i.filename.startswith(('/', '\\')) or '\\' in i.filename or i.flag_bits & 1:
                raise ValueError('不安全的文档包路径或加密文档')
        if len(set(z.namelist()))!=len(entries): raise ValueError('文档存在重复部件')
        if suffix=='.docx':
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            rels={r.get('Id'):posixpath.normpath('word/'+r.get('Target','')) for r in xml(z.read('word/_rels/document.xml.rels')) if r.get('TargetMode')!='External'} if 'word/_rels/document.xml.rels' in z.namelist() else {}
            root=xml(z.read('word/document.xml'))
            for i, element in enumerate(root.find('w:body',ns),1):
                if element.tag.endswith('}tbl'):
                    text='\n'.join(' | '.join(''.join(t.text or '' for t in cell.findall('.//w:t',ns)) for cell in row.findall('w:tc',ns)) for row in element.findall('w:tr',ns))
                else: text=''.join(t.text or '' for t in element.findall('.//w:t',ns))
                refs=[rels.get(n.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')) for n in element.iter() if n.tag.endswith('}blip')]
                if text.strip() or any(refs): blocks.append({'location':f'正文块 {i}', 'text':text,'image_parts':[r for r in refs if r], 'type':'table' if element.tag.endswith('}tbl') else 'paragraph'})
        elif suffix=='.pptx':
            ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
            rel={r.get('Id'):r.get('Target') for r in xml(z.read('ppt/_rels/presentation.xml.rels')) if r.get('TargetMode')!='External'}
            slides=xml(z.read('ppt/presentation.xml')).findall('p:sldIdLst/p:sldId',ns)
            for i,s in enumerate(slides,1):
                target=rel[s.get('{'+ns['r']+'}id')]
                name=posixpath.normpath('ppt/'+target) if not target.startswith('/') else target.lstrip('/')
                root=xml(z.read(name))
                text='\n'.join(''.join(t.text or '' for t in p.findall('.//a:t',ns)) for p in root.findall('.//a:p',ns))
                blocks.append({'location':f'幻灯片 {i}', 'text':text.strip() or '[本页无可提取文字，请查看原稿图片] '})
        else:
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            strings=[]
            if 'xl/sharedStrings.xml' in z.namelist(): strings=[''.join(t.text or '' for t in n.findall('.//s:t',ns)) for n in xml(z.read('xl/sharedStrings.xml'))]
            rel={r.get('Id'):r.get('Target') for r in xml(z.read('xl/_rels/workbook.xml.rels')) if r.get('TargetMode')!='External'}
            for sheet in xml(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns):
                target=rel[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
                name=posixpath.normpath('xl/'+target) if not target.startswith('/') else target.lstrip('/')
                for row in xml(z.read(name)).findall('.//s:sheetData/s:row',ns):
                    cells=[]
                    for cell in row.findall('s:c',ns):
                        val=cell.find('s:v',ns); text=val.text if val is not None and val.text else ''
                        if cell.get('t')=='s': text=strings[int(text)] if text else ''
                        if cell.get('t')=='inlineStr': text=''.join(t.text or '' for t in cell.findall('.//s:t',ns))
                        formula=cell.find('s:f',ns)
                        if formula is not None: text+=' [公式：'+(formula.text or '')+'；缓存值未重新计算]'
                        if text: cells.append({'cell':cell.get('r'), 'value':text})
                    if cells: blocks.append({'location':sheet.get('name')+'!'+row.get('r'), 'text':' | '.join(c['cell']+': '+c['value'] for c in cells), 'cells':cells})
        for name in z.namelist():
            ext=Path(name).suffix.lower()
            if name.startswith(('word/media/','ppt/media/')) and ext in ('.png','.jpg','.jpeg','.webp'):
                data=z.read(name)
                if valid_image(data,ext): images.append({'name':name,'raw':data,'suffix':ext})
    body='\n\n'.join('['+b['location']+']\n'+b['text'] for b in blocks)
    if len(body)>2000000: raise ValueError('提取文本规模超限')
    return {'body':body, 'blocks':blocks, 'images':images}

def valid_image(raw,ext):
    return (ext=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ('.jpg','.jpeg') and raw.startswith(b'\xff\xd8\xff')) or (ext=='.webp' and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')

def store_asset(g,c,pid,raw,title,source,category='资料'):
    ext=Path(title).suffix.lower(); digest=hashlib.sha256(raw).hexdigest()
    old=next((a for a in g['items'](c,pid,'asset') if a.get('sha256')==digest),None)
    if old:
        refs=old.get('source_refs',[])
        if source not in refs: refs.append(source); old['source_refs']=refs; g['put'](c,pid,'asset',old,old['id'])
        return old['id']
    key=g['uid']()+ext; folder=g['DB_PATH'].parent/'assets'/pid; folder.mkdir(parents=True,exist_ok=True)
    (folder/key).write_bytes(raw)
    return g['put'](c,pid,'asset',{'title':title,'category':category,'mime':MIMES[ext], 'size':len(raw),'storage_key':key,'sha256':digest,'source_refs':[source], 'rights_status':'用户提供，外部使用范围待确认'})

CLAIMS=[('性能与测试',r'盐雾|附着力|1000\s*小时|1500\s*小时','补充检测标准、基材、涂层体系、报告编号与原始报告。'),('环保与适用边界',r'零排放|无污染|所有金属|所有行业|环评','区分工艺废水、槽液、固废与整厂排放；补充项目适用条件。'),('经济测算',r'\d+\s*[%％]|\d+.*元[/／]|降本','注明基准工艺、产能、价格和测算周期，不外推为普遍承诺。'),('资质与背书',r'认证|专利|第三方|华为|中集|碳达峰','补充证书或政策原文、检测主体、有效期及对外使用授权。')]

def ingest(g,c,pid,path,category,batch):
    path=Path(path); raw=path.read_bytes(); digest=hashlib.sha256(raw).hexdigest(); source=path.name
    asset=store_asset(g,c,pid,raw,path.name,{'batch':batch,'path':str(path)},'资料')
    old=next((k for k in g['items'](c,pid,'knowledge') if k.get('source_sha256')==digest),None)
    if old: return {'knowledge_id':old['id'],'asset_id':asset,'duplicate':True,'title':path.stem}
    parsed=parse(raw,path.suffix.lower())
    image_ids=[store_asset(g,c,pid,x['raw'],path.stem+'-'+Path(x['name']).name,{'document_asset':asset,'part':x['name'],'batch':batch},'图片') for x in parsed['images']]
    image_map={x['name']:aid for x,aid in zip(parsed['images'],image_ids)}
    for b in parsed['blocks']: b['image_ids']=[image_map[p] for p in b.get('image_parts',[]) if p in image_map]
    kid=g['put'](c,pid,'knowledge',{'title':path.stem,'category':category,'body':parsed['body'],'source':source,'status':'pending','version':1,'source_sha256':digest,'asset_id':asset,'image_ids':image_ids,'blocks':parsed['blocks'],'import_batch':batch,'origin':'customer_source'})
    count=0
    for label,pattern,requirement in CLAIMS:
        matches=[b for b in parsed['blocks'] if re.search(pattern,b['text'])]
        if matches:
            g['put'](c,pid,'evidence_claim',{'title':label,'knowledge_id':kid,'source_title':path.stem,'status':'pending','requirement':requirement,'excerpts':[{'location':b['location'],'text':b['text']} for b in matches],'source_version':1,'import_batch':batch}); count+=1
    return {'knowledge_id':kid,'asset_id':asset,'duplicate':False,'title':path.stem,'blocks':len(parsed['blocks']),'images':len(image_ids),'claim_groups':count}
