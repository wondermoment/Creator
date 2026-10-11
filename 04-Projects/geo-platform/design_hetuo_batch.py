"""Render and version 22 approved-scope article designs from reviewed editorial copy."""
import argparse
import copy
import hashlib
import html
import json
import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from design_hetuo_value_sample import ROOT, PROJECT, CONTENT, TEMPLATE
from design_hetuo_article_cards import Canvas, INK, GREEN, MUTED
from hetuo_batch_art_direction import ART

OUT=ROOT/'outputs/hetuo-redesign'
SNAP=ROOT/'.runtime/article-design-context.json'
STYLE='context-values-20261002-v2'


def card(spec, style, dest):
    title, sub, raw=spec.split('|');points=[p.split(':',1) for p in raw.split(';')]
    assert len(points)==3
    a=Canvas()
    a.text(470,50,'和拓化学 / 技术与采购参考',27,GREEN,True)
    if style==0:
        a.text(460,120,title, min(98, int(1480/len(title))),bold=True)
        a.text(470,266,sub,40,MUTED)
        for i,(key,detail) in enumerate(points):
            x=470+i*493
            a.line((x,360,x+70,360),GREEN,7)
            a.text(x,390,key,60,GREEN,True,width=465)
            a.text(x,481,detail,31,MUTED,width=465)
    elif style==1:
        # Thesis at left, three practical considerations on the right.
        split=title.find('，')
        if split<0: split=(len(title)+1)//2
        left,right=title[:split],title[split:].lstrip('，')
        a.text(462,157,left,min(84,int(650/max(1,len(left)))),bold=True,width=665)
        a.text(462,278,right,min(84,int(650/max(1,len(right)))),GREEN,True,width=665)
        # Supporting sentence may wrap into two readable lines.
        subparts=[sub] if len(sub)<=16 else [sub[:16],sub[16:]]
        for n,t in enumerate(subparts):a.text(472,434+n*45,t,34,MUTED,width=650)
        a.line((1150,134,1150,525),'#cce4df')
        for i,(key,detail) in enumerate(points):
            y=135+i*133
            a.text(1210,y,key,57,GREEN,True,width=735)
            a.text(1214,y+77,detail,33,MUTED,width=735)
    elif style==2:
        a.text(460,121,title,min(96,int(1480/len(title))),bold=True)
        a.text(470,256,sub,39,MUTED)
        for i,(key,detail) in enumerate(points):
            x=470+i*495
            a.rect((x,350,x+459,530),'#edf7f4' if i%2==0 else '#f0f5f8')
            a.text(x+22,377,key,56,GREEN,True,width=418)
            a.text(x+22,466,detail,29,MUTED,width=418)
    else:
        a.text(461,113,title,min(92,int(1480/len(title))),bold=True)
        a.text(470,241,sub,38,MUTED)
        for i,(key,detail) in enumerate(points):
            y=329+i*76
            a.rect((470,y,483,y+42),GREEN)
            a.text(513,y,key,44,GREEN,True,width=420)
            a.text(970,y+4,detail,38,MUTED,width=965)
            if i<2:a.line((513,y+59,1950,y+59),'#d8e9e6')
    a.im.save(dest,optimize=True)
    return {'title':title,'takeaway':sub,'points':points,'composition':style}


def cover(photo,logo,lines,deck,style,dest):
    photo=photo.convert('RGB');im=Image.new('RGB',(1800,900),'#f2f7f6')
    if style==0:
        im=ImageOps.fit(photo,(1800,900),centering=(.5,.45)).convert('RGBA')
        mask=Image.new('RGBA',im.size);d=ImageDraw.Draw(mask)
        for x in range(1800):d.line((x,0,x,900),fill=(9,43,54,round(241-133*min(1,max(0,(x-500)/1200)))))
        im=Image.alpha_composite(im,mask).convert('RGB');x=90;ink='#ffffff';accent='#62dbc0';muted='#c4e3dd';width=1400
    elif style==1:
        im.paste(ImageOps.fit(photo,(880,900),centering=(.5,.45)),(920,0));x=75;ink=INK;accent=GREEN;muted=MUTED;width=805
    elif style==2:
        im=Image.new('RGB',(1800,900),INK);im.paste(ImageOps.fit(photo,(790,900),centering=(.5,.45)),(0,0));x=858;ink='white';accent='#67debf';muted='#c6dfde';width=850
    else:
        im.paste(ImageOps.fit(photo,(1800,900),centering=(.5,.45)),(0,0))
        overlay=Image.new('RGBA',im.size,(0,0,0,0));od=ImageDraw.Draw(overlay);od.rectangle((0,0,1800,240),fill=(9,43,54,130));od.rectangle((0,240,1800,900),fill=(9,43,54,220));im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
        x=90;ink='white';accent='#69dcc0';muted='#c4e3dd';width=1590
    d=ImageDraw.Draw(im)
    def text(px,y,t,size,color,bold=False,maxw=1600):
        size=min(size,int(maxw/max(1,len(t))))
        font=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',size)
        assert px+d.textlength(t,font=font)<=1760,(t,px,size)
        d.text((px,y),t,font=font,fill=color,anchor='lt')
    d.rectangle((0,0,1800,10),fill=GREEN)
    d.rectangle((x,58,x+178,178),fill='white');mark=ImageOps.contain(logo.convert('RGB'),(164,106));im.paste(mark,(x+89-mark.width//2,118-mark.height//2))
    text(x+208,78,'和拓化学',41,ink,True,maxw=width-215)
    text(x+208,137,'技术与采购指南',24,muted,maxw=width-215)
    for i,t in enumerate(lines):text(x-5,288+i*158,t,122 if style in (0,3) else 104,ink if i==0 else accent,True,maxw=width)
    d.line((x,659,x+120,659),fill=accent,width=6)
    text(x,707,deck,39,ink,maxw=width)
    text(x,816,'WWW.HEROTO.COM.CN',24,muted,maxw=width)
    im.save(dest,optimize=True)


def render_all():
    rows=json.loads(SNAP.read_text(encoding='utf-8'))
    photos=json.loads((ROOT/'.runtime/cover-photo-options.json').read_text(encoding='utf-8'))+json.loads((ROOT/'.runtime/cover-more.json').read_text(encoding='utf-8'))
    folder=ROOT/'.runtime/assets'/PROJECT
    logo=Image.open(folder/photos[20][1]['storage_key'])
    OUT.mkdir(parents=True,exist_ok=True);manifest=[]
    for k,(idx,photoidx,line1,line2,deck,copytext) in enumerate(ART):
        row=rows[idx];assert row['id']!=CONTENT
        directory=OUT/row['id'];directory.mkdir(exist_ok=True)
        sourceid,source=photos[photoidx]
        cover(Image.open(folder/source['storage_key']),logo,[line1,line2],deck,k%4,directory/'cover.png')
        specs=[s.strip() for s in copytext.strip().splitlines() if s.strip()];assert len(specs)==4
        figures=[]
        for j,spec in enumerate(specs):
            data=card(spec,(k+j)%4,directory/f'figure-{j+1}.png')
            n=row['layout']['figures'][j]['after']
            data.update(after=n,source_blocks=[{'index':b,'text':row['layout']['blocks'][b].get('text','')} for b in range(max(0,n-2),min(len(row['layout']['blocks']),n+4))])
            figures.append(data)
        manifest.append({'id':row['id'],'title':row['title'],'revision':row['revision'],'body_sha256':hashlib.sha256(row['body'].encode()).hexdigest(),'prior_layout_sha256':hashlib.sha256(json.dumps(row['layout'],sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'cover':{'lines':[line1,line2],'deck':deck,'source_asset_id':sourceid,'source_sha256':source.get('sha256'),'composition':k%4},'figures':figures})
    assert len(manifest)==22 and len({m['cover']['source_asset_id'] for m in manifest})==22
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Each sheet shows one complete article, at a width useful for visual inspection.
    for m in manifest:
        page=Image.new('RGB',(1100,1970),'#eaf0f2');directory=OUT/m['id']
        img=Image.open(directory/'cover.png');img.thumbnail((1050,525));page.paste(img,(25,20))
        for j in range(4):
            img=Image.open(directory/f'figure-{j+1}.png');img.thumbnail((1050,320));page.paste(img,(25,570+j*345))
        page.save(directory/'contact.jpg',quality=88)
    for start in (0,8,16):
        subset=manifest[start:start+8];sheet=Image.new('RGB',(1600,((len(subset)+1)//2)*430),'#eaf0f2');d=ImageDraw.Draw(sheet)
        for n,m in enumerate(subset):
            im=Image.open(OUT/m['id']/'cover.png');im.thumbnail((780,390));x=(n%2)*800;y=(n//2)*430;sheet.paste(im,(x+10,y+10));d.text((x+20,y+405),str(start+n+1)+' / '+m['id'][:8],fill='black')
        sheet.save(OUT/f'covers-{start+1:02d}.jpg',quality=92)
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>和拓配图设计总览</title><style>body{font:16px system-ui;background:#edf2f3;margin:24px}section{background:white;padding:24px;margin:20px auto;max-width:1050px}img{max-width:100%;display:block;margin:18px auto}h2{font-size:20px}</style><h1>和拓 · 22篇图文设计预览</h1><p>封面与正文价值图；未批准发布。</p>'+''.join('<section><h2>'+html.escape(m['title'])+'</h2><img src="'+m['id']+'/cover.png">'+''.join('<img src="'+m['id']+f'/figure-{j+1}.png">' for j in range(4))+'</section>' for m in manifest),encoding='utf-8')
    return manifest


def apply_all():
    import server as s
    from sample_review import layout_current
    from source_import import store_asset
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    with s.db() as c:
        assert s.project(c,PROJECT)['website'].rstrip('/')=='https://www.heroto.com.cn'
        pending=[]
        for m in manifest:
            row=s.resource(c,PROJECT,m['id'],'content')
            if row.get('layout',{}).get('design_batch')==STYLE:continue
            assert row['revision']==m['revision'] and row['status'] in ('draft','pending','rejected') and layout_current(row),m['id']
            assert hashlib.sha256(row['body'].encode()).hexdigest()==m['body_sha256']
            assert hashlib.sha256(json.dumps(row['layout'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()==m['prior_layout_sha256']
            assert not any(p.get('content_id')==m['id'] and p['status']!='cancelled' for p in s.items(c,PROJECT,'publication'))
            assert not any(j.get('status') in ('queued','running') and j.get('payload',{}).get('content_id')==m['id'] for j in s.items(c,PROJECT,'execution'))
            s.resource(c,PROJECT,m['cover']['source_asset_id'],'asset')
            pending.append((m,row))
        updated=[]
        for m,row in pending:
            row.setdefault('history',[]).append(copy.deepcopy({k:row.get(k) for k in ('revision','title','body','status','channels','layout','platform_payloads')}))
            directory=OUT/m['id'];changes={};assets=[]
            for j in range(5):
                design=m['cover'] if j==0 else m['figures'][j-1]
                old=row['layout']['cover_id'] if j==0 else row['layout']['figures'][j-1]['asset_id']
                file=directory/('cover.png' if j==0 else f'figure-{j}.png')
                aid=store_asset(vars(s),c,PROJECT,file.read_bytes(),m['id']+('-新版封面.png' if j==0 else f'-价值图{j}.png'),{'type':'context_editorial_design','content_id':m['id'],'source_revision':m['revision'],'body_sha256':m['body_sha256'],'design':design,'replaces_asset_id':old,'batch':STYLE},'图片')
                asset=s.resource(c,PROJECT,aid,'asset');asset.update(collection='和拓文章品牌配图',tags=['和拓实业','封面' if j==0 else '价值提炼','客户审阅'],description=' / '.join(design['lines']) if j==0 else design['title']);s.put(c,PROJECT,'asset',asset,aid)
                assets.append(aid);changes[old]=aid
            row['layout']['cover_id']=assets[0]
            for j,f in enumerate(row['layout']['figures']):f.update(asset_id=assets[j+1],caption=m['figures'][j]['title']+' · '+m['figures'][j]['takeaway'])
            row['layout']['design_batch']=STYLE
            for variant in row.get('platform_payloads',{}).values():
                variant['cover_id']=assets[0];variant['attachment_ids']=[changes.get(a,a) for a in variant.get('attachment_ids',[])]
            row.pop('quality',None);row.update(revision=row['revision']+1,status='pending',approved_revision=None,review_note='',preparation_status='差异化封面与4张上下文价值图 · 待客户审阅')
            row['review_notes']=[n for n in row.get('review_notes',[]) if '本版使用客户提供的和拓配图模板，共5张' not in n]
            row['review_notes'].append('已按上下文重做封面与四张价值图；封面背景来自本企业图库，使用范围与最终渠道裁切待核准。')
            s.put(c,PROJECT,'content',row,m['id']);updated.append(m['id'])
        if updated:s.event(c,PROJECT,'local-design-assistant','按用户确认风格更新文章配图',f'{len(updated)}篇，每篇封面及4张价值图；保留样版、原文、来源与历史；未发布')
    (OUT/'applied.json').write_text(json.dumps({'updated':updated,'published':False},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'updated':len(updated),'images':len(updated)*5,'published':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(apply_all() if a.apply else {'rendered':len(render_all())})
