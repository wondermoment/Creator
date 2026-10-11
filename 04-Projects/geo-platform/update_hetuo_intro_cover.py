"""Apply the customer's image153 background to the explicitly selected article."""
import copy
import hashlib
import json
from pathlib import Path
import server as s
from source_import import store_asset
from sample_review import layout_current, require_current_sources, render_reader, embedded_asset_url
from preview_images import render_images

PID = 'a46fb911b04fbf0b783c7bf5'
RID = '9c8fd4efd0f7de9f21b0c97a'
ROOT = Path(__file__).resolve().parent


def apply():
    original=Path('F:/2026.9.1/图片153.jpg')
    output=ROOT/'outputs/和拓-硅晶是什么-新封面.png'
    expected=json.loads((ROOT/'.runtime/intro-cover-before.json').read_text(encoding='utf-8'))
    with s.db() as c:
        assert s.project(c,PID)['website'].rstrip('/')=='https://www.heroto.com.cn'
        before={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        row=s.resource(c,PID,RID,'content')
        assert row['revision']==expected['revision']==5 and row['layout']==expected['layout'] and row['body']==expected['body']
        assert row['status']=='pending' and layout_current(row)
        require_current_sources(vars(s),c,PID,row)
        assert not any(p.get('content_id')==RID and p['status']!='cancelled' for p in s.items(c,PID,'publication'))
        assert not any(j.get('status') in ('queued','running') and (j.get('content_id')==RID or j.get('payload',{}).get('content_id')==RID) for j in s.items(c,PID,'execution'))
        photo=store_asset(vars(s),c,PID,original.read_bytes(),original.name,{'type':'user_supplied_cover_background','path':str(original),'content_id':RID},'图片')
        asset=s.resource(c,PID,photo,'asset')
        asset.update(collection='和拓文章品牌配图',tags=['和拓实业','客户提供','封面背景'],description='客户指定科技概念背景，用于视觉设计，不作为实际微观结构或性能证据。')
        s.put(c,PID,'asset',asset,photo)
        old=row['layout']['cover_id']
        aid=store_asset(vars(s),c,PID,output.read_bytes(),output.name,{'type':'user_requested_cover_replacement','content_id':RID,'source_revision':5,'source_asset_id':photo,'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'replaces_asset_id':old,'copy':['硅晶是什么','新手先看这篇','原理 · 流程 · 适用边界']},'图片')
        asset=s.resource(c,PID,aid,'asset');asset.update(collection='和拓文章品牌配图',tags=['和拓实业','文章封面','客户指定背景']);s.put(c,PID,'asset',asset,aid)
        row.setdefault('history',[]).append(copy.deepcopy({k:row.get(k) for k in ('revision','title','body','channels','status','layout','platform_payloads')}))
        row['layout'].update(cover_id=aid,background_update='customer-image153-20261002')
        for variant in row.get('platform_payloads',{}).values():
            variant['cover_id']=aid
            variant['attachment_ids']=[aid if x==old else x for x in variant.get('attachment_ids',[])]
        row.update(revision=6,status='pending',approved_revision=None,review_note='');row.pop('quality',None)
        s.put(c,PID,'content',row,RID)
        after={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        assert [key for key in before if before[key]!=after[key]]==[RID]
        assert row['layout']['figures']==expected['layout']['figures'] and row['sources']==expected['sources'] and row['title']==expected['title']
        s.event(c,PID,'local-design-assistant','按客户指定图片替换单篇封面',RID+' · v5 → v6 · 仅封面背景调整，正文与四张正文图保留')
        document=render_reader(s.project(c,PID),row,embedded_asset_url(vars(s),c,PID))
        record={'content_id':RID,'old_revision':5,'new_revision':6,'old_cover_id':old,'new_cover_id':aid,'source_asset_id':photo,'changed_content_count':1,'published':False}
    (ROOT/'outputs/hetuo-intro-cover-update.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'outputs/和拓-硅晶是什么-客户预览-v6.html').write_text(document,encoding='utf-8')
    (ROOT/'outputs/和拓-硅晶是什么-客户预览长图-v6.png').write_bytes(render_images(document))
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    apply()
