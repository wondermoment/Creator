"""Single-article scene-photo sample requested by the customer; no bulk rollout."""
import copy
import hashlib
import json
from pathlib import Path
from PIL import Image
import server as s
from sample_review import layout_current, require_current_sources, render_reader, embedded_asset_url
from preview_images import render_images

ROOT=Path(__file__).resolve().parent
PID='a46fb911b04fbf0b783c7bf5'
RID='9c8fd4efd0f7de9f21b0c97a'
SCENES=[
    ('c001d1a10b008d3684754f1d',0,'2025 中国国际表面处理展 · 和拓展台与现场交流', '开篇：从真实展台引入硅晶产品与应用认知'),
    ('745d60572cb24ae11574bb20',18,'崇明东滩 · 金属表面处理及涂装技术培训现场', '中段：衔接不同处理工艺的知识说明'),
    ('6bb3a7a6b48fd6550b73f9ca',37,'2025 中国国际表面处理展 · 现场交流剪影', '结尾：呼应工况沟通与选型判断'),
]


def main():
    with s.db() as c:
        assert s.project(c,PID)['website'].rstrip('/')=='https://www.heroto.com.cn'
        baseline={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        row=s.resource(c,PID,RID,'content')
        assert row['revision']==6 and row['status']=='pending' and layout_current(row)
        assert len(row['layout']['figures'])==4
        require_current_sources(vars(s),c,PID,row)
        assert not any(p.get('content_id')==RID and p['status']!='cancelled' for p in s.items(c,PID,'publication'))
        assert not any(j.get('status') in ('queued','running') and (j.get('content_id')==RID or j.get('payload',{}).get('content_id')==RID) for j in s.items(c,PID,'execution'))
        before=copy.deepcopy(row)
        provenance=[]
        for aid,position,caption,rationale in SCENES:
            asset=s.resource(c,PID,aid,'asset')
            assert asset.get('source_refs') and asset.get('related_knowledge_ids')
            path=ROOT/'.runtime/assets'/PID/asset['storage_key']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['sha256']
            with Image.open(path) as im:
                assert im.width>=800 and im.height>=400
                im.verify()
            origins=[]
            for kid in asset['related_knowledge_ids']:
                doc=s.resource(c,PID,kid,'knowledge')
                origins.append({'id':kid,'title':doc['title'],'version':doc['version']})
            row['layout']['figures'].append({'asset_id':aid,'after':position,'caption':caption,'type':'scene_photo'})
            provenance.append({'asset_id':aid,'sha256':asset['sha256'],'after':position,'caption':caption,'rationale':rationale,'source_refs':asset['source_refs'],'source_documents':origins})
        row['layout']['scene_photo_sample']={'version':1,'sources':provenance}
        row.setdefault('history',[]).append({k:copy.deepcopy(before.get(k)) for k in ('revision','title','body','channels','status','layout','platform_payloads')})
        for variant in row.get('platform_payloads',{}).values():
            variant['attachment_ids']=list(dict.fromkeys(variant.get('attachment_ids',[])+[x[0] for x in SCENES]))
        row.update(revision=7,approved_revision=None,review_note='',preparation_status='封面、4张价值图与3张实景照片 · 待客户审阅')
        row.pop('quality',None)
        row.setdefault('review_notes',[]).append('本篇新增3张公众号原始实景照片，开篇展台、中段技术培训、结尾展会交流；仅作场景展示，不代表正文性能参数的检测证据。')
        s.put(c,PID,'content',row,RID)
        after={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        assert [key for key in baseline if baseline[key]!=after[key]]==[RID]
        for key in ('title','body','sources','channels'):assert row[key]==before[key]
        assert row['layout']['cover_id']==before['layout']['cover_id']
        assert row['layout']['figures'][:4]==before['layout']['figures']
        assert row['layout']['blocks']==before['layout']['blocks']
        s.event(c,PID,'local-design-assistant','入门篇实景照片搭配样版',RID+' · v6 → v7 · 仅本篇增加3张原始公众号照片；未发布')
        document=render_reader(s.project(c,PID),row,embedded_asset_url(vars(s),c,PID))
        assert document.count('<img ')==8
    out=ROOT/'outputs'
    (out/'hetuo-intro-scenes-v7.json').write_text(json.dumps({'article_id':RID,'revision':7,'sources':provenance,'changed_articles':1,'published':False},ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'和拓-硅晶入门-实景搭配预览-v7.html').write_text(document,encoding='utf-8')
    image=render_images(document)
    (out/'和拓-硅晶入门-实景搭配长图-v7.png').write_bytes(image)
    print(json.dumps({'revision':7,'images':8,'added_scenes':3,'changed_articles':1,'png_bytes':len(image)},ensure_ascii=False))


if __name__=='__main__':main()
