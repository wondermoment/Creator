"""Editorial cover from customer-owned library assets; one article only."""
import argparse
import copy
import hashlib
import json
import sqlite3
from PIL import Image, ImageDraw, ImageFont, ImageOps
from design_hetuo_value_sample import ROOT, PROJECT, CONTENT

PHOTO = 'f7020eeeb4d895784378e30c'
LOGO = '1a67ef5955323508f7f474ad'
OLD = '4a7d6fe681f9a59f848a7cd8'
OUT = ROOT/'outputs'/'hetuo-article-cover-v2.png'
COPY = ['硅晶前处理', '厂家怎么选？', '工艺 · 验证 · 成本', '和拓化学', '技术与采购指南']


def render():
    with sqlite3.connect('file:'+str(ROOT/'.runtime/geo.db')+'?mode=ro', uri=True) as c:
        assets = {}
        for aid in (PHOTO, LOGO):
            row = c.execute("select data from resources where project_id=? and id=? and kind='asset'", (PROJECT, aid)).fetchone()
            assert row, 'Missing enterprise source asset'
            assets[aid] = json.loads(row[0])
    folder = ROOT/'.runtime/assets'/PROJECT
    photo = Image.open(folder/assets[PHOTO]['storage_key']).convert('RGB')
    im = ImageOps.fit(photo, (1800, 900), centering=(0.58, 0.45)).convert('RGBA')
    shade = Image.new('RGBA', im.size)
    d = ImageDraw.Draw(shade)
    for x in range(1800):
        # Strong reading contrast at left, retain recognizable factory detail at right.
        alpha = round(244 - 142*min(1, max(0, (x-550)/1050)))
        d.line((x,0,x,900), fill=(9,43,54,alpha))
    im = Image.alpha_composite(im, shade).convert('RGB')
    d = ImageDraw.Draw(im)
    def text(x,y,value,size,color,bold=False):
        font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc', size)
        assert x+d.textlength(value,font=font)<1740
        d.text((x,y),value,font=font,fill=color,anchor='lt')
    for x in range(1800):
        t=x/1800;d.line((x,0,x,10),fill=(round(26+15*t),round(166-47*t),round(141+34*t)))
    logo = Image.open(folder/assets[LOGO]['storage_key']).convert('RGB')
    logo = ImageOps.contain(logo,(184,114))
    d.rectangle((90,65,290,195),fill='white')
    im.paste(logo,(190-logo.width//2,130-logo.height//2))
    text(326,86,'和拓化学',45,'#ffffff',True)
    text(328,149,'HEROTO  /  技术与采购指南',24,'#afe1da')
    text(82,266,'硅晶前处理',142,'#ffffff',True)
    text(80,444,'厂家怎么选？',142,'#63ddc1',True)
    d.line((94,653,230,653),fill='#56d2b9',width=7)
    text(92,703,'工艺 · 验证 · 成本',53,'#ffffff',True)
    text(95,807,'WWW.HEROTO.COM.CN',25,'#b7d4d7')
    # Photo stays a source illustration, never described as proof of a performance claim.
    OUT.parent.mkdir(exist_ok=True)
    im.save(OUT,optimize=True)
    return OUT.read_bytes()


def apply(raw):
    import server as s
    from sample_review import layout_current
    from source_import import store_asset
    with s.db() as c:
        assert s.project(c,PROJECT)['website'].rstrip('/')=='https://www.heroto.com.cn'
        item=s.resource(c,PROJECT,CONTENT,'content')
        if item.get('layout',{}).get('editorial_cover')=='20261002-v1':
            return {'unchanged':True,'revision':item['revision']}
        assert item['revision']==4 and item['status']=='pending' and layout_current(item)
        assert item['layout']['cover_id']==OLD
        assert not any(p.get('content_id')==CONTENT and p['status']!='cancelled' for p in s.items(c,PROJECT,'publication'))
        assert not any(j.get('status') in ('queued','running') and j.get('payload',{}).get('content_id')==CONTENT for j in s.items(c,PROJECT,'execution'))
        sources=[s.resource(c,PROJECT,rid,'asset') for rid in (PHOTO,LOGO)]
        item.setdefault('history',[]).append(copy.deepcopy({k:item.get(k) for k in ('revision','title','body','channels','status','layout','platform_payloads')}))
        aid=store_asset(vars(s),c,PROJECT,raw,'和拓-硅晶前处理厂家怎么选-文章封面.png',{
            'type':'article_editorial_cover','content_id':CONTENT,'source_revision':4,'copy':COPY,
            'source_assets':[{'id':a['id'],'sha256':a.get('sha256')} for a in sources],
            'body_sha256':hashlib.sha256(item['body'].encode()).hexdigest(),'replaces_asset_id':OLD,
        },'图片')
        asset=s.resource(c,PROJECT,aid,'asset')
        asset.update(collection='和拓文章品牌配图',tags=['和拓实业','文章封面','实景素材'],description='使用和拓资料中的厂房照片与品牌标识，封面短标题与工艺/验证/成本阅读重点。')
        s.put(c,PROJECT,'asset',asset,aid)
        item['layout'].update(cover_id=aid,editorial_cover='20261002-v1')
        for variant in item.get('platform_payloads',{}).values():variant['cover_id']=aid
        item.pop('quality',None)
        item.update(revision=5,approved_revision=None,review_note='',preparation_status='实景封面与4张价值图已排版 · 待客户审阅')
        item.setdefault('review_notes',[]).append('封面改用企业资料实景和大标题；渠道裁切及素材使用范围仍需审阅。')
        s.put(c,PROJECT,'content',item,CONTENT)
        s.event(c,PROJECT,'local-design-assistant','更新单篇文章实景封面',CONTENT+' · v4 → v5 · 用户授权替换封面，保留正文及4张价值图')
        return {'revision':5,'cover_id':aid}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    raw=render();print(apply(raw) if a.apply else str(OUT))
