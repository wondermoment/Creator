"""User-approved rollout of the reviewed summit QR white mask, tenant scoped."""
import copy
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
import server as s
from sample_review import (layout_current, require_current_sources, render_reader,
                           embedded_asset_url, require_unchanged_preview_assets)
from preview_images import render_images

ROOT = Path(__file__).resolve().parent
PID = 'a46fb911b04fbf0b783c7bf5'
OUT = ROOT / 'outputs/hetuo-qr-clean-previews'
BOX = (980,630,1080,720)

def apply():
    OUT.mkdir(parents=True,exist_ok=True)
    plan=json.loads((ROOT/'.runtime/qr-summit-plan.json').read_text(encoding='utf-8'))
    assert len(plan)==68
    mapping={};assets=[];changed=[]
    with s.db() as c:
        assert s.project(c,PID)['website'].rstrip('/')=='https://www.heroto.com.cn'
        assert not any(j.get('status') in ('queued','running') for j in s.items(c,PID,'execution'))
        baseline={r['id']:(r['project_id'],r['kind'],r['data']) for r in c.execute('SELECT * FROM resources')}
        (OUT/'before-resources.json').write_text(json.dumps({k:v for k,v in baseline.items() if v[0]==PID and (v[1]=='content' or k in {x['id'] for x in plan})},ensure_ascii=False),encoding='utf-8')
        existing=s.items(c,PID,'asset')
        for entry in plan:
            aid=entry['id'];orig=s.resource(c,PID,aid,'asset')
            source=ROOT/'.runtime/assets'/PID/orig['storage_key']
            raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==orig['sha256']
            im=Image.open(io.BytesIO(raw)).convert('RGB');assert im.size==(1080,720)
            edited=im.copy();ImageDraw.Draw(edited).rectangle((980,630,1079,719),fill='white')
            diff=ImageChops.difference(im,edited).getbbox()
            assert diff and diff[0]>=980 and diff[1]>=630 and diff[2]<=1080 and diff[3]<=720
            assert edited.crop(BOX).getextrema()==((255,255),(255,255),(255,255))
            buffer=io.BytesIO();edited.save(buffer,format='PNG');clean=buffer.getvalue();sha=hashlib.sha256(clean).hexdigest()
            reuse=next((a for a in existing if a.get('derived_from_asset_id')==aid and a.get('sha256')==sha),None)
            if reuse:
                new_id=reuse['id'];key=reuse['storage_key'];assert (source.parent/key).read_bytes()==clean
            else:
                key='qr-clean-'+sha[:24]+'.png';(source.parent/key).write_bytes(clean)
                asset={k:copy.deepcopy(v) for k,v in orig.items() if k not in ('id','kind','created','updated')}
                asset.update(title=orig['title']+' · 去二维码版',storage_key=key,mime='image/png',size=len(clean),sha256=sha,
                             derived_from_asset_id=aid,edit_provenance={'operation':'white_rectangle','box':list(BOX),'original_sha256':orig['sha256'],'requested_scope':'approved-library-rollout'},
                             description='已按客户确认样版将右下角二维码区域填白。原始照片保留，可追溯原始文档；文章使用本处理版。')
                asset['tags']=list(dict.fromkeys(asset.get('tags',[])+['去二维码','文章配图可用']))
                new_id=s.put(c,PID,'asset',asset)
            mapping[aid]=new_id
            orig.update(preferred_edited_asset_id=new_id,description=orig.get('description','')+' 原始留档：含右下角二维码，文章配图请使用关联去二维码版。')
            orig['tags']=list(dict.fromkeys(orig.get('tags',[])+['含二维码原图','原始留档']))
            s.put(c,PID,'asset',orig,aid)
            assets.append({'original_asset_id':aid,'asset_id':new_id,'sha256':sha,'storage_key':key,'original_sha256':orig['sha256'],'box':BOX,'reused':bool(reuse)})
        for row in s.items(c,PID,'content'):
            before=copy.deepcopy(row);hits=[]
            layout=row.get('layout',{})
            for f in layout.get('figures',[]):
                if f.get('asset_id') in mapping:
                    old=f['asset_id'];f['asset_id']=mapping[old];hits.append(old)
            if layout.get('cover_id') in mapping:
                old=layout['cover_id'];layout['cover_id']=mapping[old];hits.append(old)
            for variant in row.get('platform_payloads',{}).values():
                for field in ('cover_asset_id','cover_id'):
                    if variant.get(field) in mapping:
                        old=variant[field];variant[field]=mapping[old];hits.append(old)
                for field in ('attachment_ids','asset_ids'):
                    if field in variant:
                        hits.extend(a for a in variant[field] if a in mapping)
                        variant[field]=[mapping.get(a,a) for a in variant[field]]
            if not hits:continue
            assert row['status']=='pending' and layout_current(row)
            require_current_sources(vars(s),c,PID,row)
            assert not any(p.get('content_id')==row['id'] and p['status']!='cancelled' for p in s.items(c,PID,'publication'))
            row.setdefault('history',[]).append({k:copy.deepcopy(before.get(k)) for k in ('revision','title','body','channels','status','layout','platform_payloads')})
            layout.setdefault('asset_edits',[]).extend({'original_asset_id':aid,'asset_id':mapping[aid],'operation':'右下角二维码区域填白','box':list(BOX)} for aid in sorted(set(hits)))
            row.update(revision=row['revision']+1,approved_revision=None,review_note='')
            row.pop('quality',None)
            s.put(c,PID,'content',row,row['id'])
            for k in ('body','title','sources','channels'):assert row[k]==before[k]
            changed.append({'id':row['id'],'title':row['title'],'revision':row['revision'],'replaced_assets':sorted(set(hits))})
        for row in s.items(c,PID,'content'):
            assert not any(f.get('asset_id') in mapping for f in row.get('layout',{}).get('figures',[]))
            assert row.get('layout',{}).get('cover_id') not in mapping
        after={r['id']:(r['project_id'],r['kind'],r['data']) for r in c.execute('SELECT * FROM resources')}
        allowed=set(mapping)|{m['id'] for m in changed}
        assert all(after[k]==v for k,v in baseline.items() if k not in allowed)
        assert all(after[k][0]==PID and after[k][1]=='asset' for k in set(after)-set(baseline))
        s.event(c,PID,'local-design-assistant','图库峰会二维码批量填白',f'{len(mapping)}个原图记录关联处理版；{len(changed)}篇文章升版；原图保留，未发布')
    manifest={'assets':assets,'articles':changed,'other_tenant_resources_unchanged':True,'original_files_preserved':True}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',len(assets),'clean asset mappings; updated',len(changed),'articles',flush=True)

def export():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'outputs/hetuo-scene-previews/verification.json').read_text(encoding='utf-8'))
    results=[]
    for i,previous in enumerate(old,1):
        rid=previous['id'];snaps={}
        with s.db() as c:
            row=s.resource(c,PID,rid,'content');require_current_sources(vars(s),c,PID,row);assert layout_current(row)
            document=render_reader(s.project(c,PID),row,embedded_asset_url(vars(s),c,PID,snaps))
            revision=row['revision'];layout=copy.deepcopy(row['layout'])
        name=f'{i:02d}-'+re.sub(r'[<>:"/\\|?*]','',row['title'])[:65]+f'-v{revision}'
        oldhtml=ROOT/'outputs/hetuo-scene-previews'/Path(previous['file']).with_suffix('.html')
        oldpng=oldhtml.with_suffix('.png')
        if (OUT/(name+'.html')).exists() and (OUT/(name+'.png')).exists():
            oldhtml=OUT/(name+'.html');oldpng=OUT/(name+'.png')
        raw=oldpng.read_bytes() if oldhtml.exists() and oldhtml.read_text(encoding='utf-8')==document else render_images(document)
        with s.db() as c:
            current=s.resource(c,PID,rid,'content');assert current['revision']==revision and current['layout']==layout
            require_current_sources(vars(s),c,PID,current);require_unchanged_preview_assets(vars(s),c,PID,snaps)
        assert document.count('<img ')==8
        with Image.open(io.BytesIO(raw)) as im:assert im.width==860;dims=im.size;im.verify()
        (OUT/(name+'.html')).write_text(document,encoding='utf-8');(OUT/(name+'.png')).write_bytes(raw)
        results.append({'id':rid,'revision':revision,'file':name+'.png','dimensions':dims,'images':8})
        print('Exported',i,'/23',flush=True)
    for ext,label in [('png','长图'),('html','HTML')]:
        path=ROOT/f'outputs/和拓-23篇去二维码预览-{label}.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            for r in results:
                f=OUT/Path(r['file']).with_suffix('.'+ext);z.write(f,f.name)
        with zipfile.ZipFile(path) as z:assert z.testzip() is None and len(z.namelist())==23
    (OUT/'verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    unique={a['sha256']:a for a in manifest['assets']}
    sheet=Image.new('RGB',(1200,((len(unique)+3)//4)*220),'#ecf0f2');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
    for i,a in enumerate(unique.values()):
        im=Image.open(ROOT/'.runtime/assets'/PID/a['storage_key']).convert('RGB');im.thumbnail((290,194));x=i%4*300;y=i//4*220;sheet.paste(im,(x,y));draw.text((x+8,y+196),f'{i+1:02d} · 右下角已填白',fill='#24464c',font=font)
    sheet.save(OUT/'图库去二维码总览.jpg',quality=92)

if __name__=='__main__':
    import sys
    if '--export' in sys.argv:export()
    else:apply()
