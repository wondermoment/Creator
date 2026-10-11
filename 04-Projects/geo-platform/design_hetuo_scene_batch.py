"""Customer-authorized rollout: three editorially selected real photos per article."""
import argparse
import base64
import copy
import hashlib
import html
import io
import json
import re
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PID='a46fb911b04fbf0b783c7bf5'
SAMPLE='9c8fd4efd0f7de9f21b0c97a'
OUT=ROOT/'outputs/hetuo-scene-previews'
# Frozen article index: [opening, middle, ending] candidate indices; middle paragraph.
# Each photo was visually inspected; captions describe the actual event, not test results.
PLAN={
 0:([10,92,54],22,'涂装问题诊断：样品交流、工艺培训、展台讨论'),
 1:([113,102,117],27,'质量与验收：行业展台、技术培训、方案交流'),
 2:([201,170,208],68,'供应商与趋势：行业大会、双碳分享、海外展台交流'),
 4:([51,157,161],24,'老板选型：企业展台、工艺简化分享、行业交流'),
 5:([49,197,56],16,'降本与改造：方案展示、前处理痛点分享、展台讨论'),
 6:([138,105,173],20,'应用可靠性：参展记录、清洗知识培训、方案交流'),
 7:([230,93,233],23,'工艺对比：涂装峰会、技术培训、材料方案交流'),
 8:([53,215,179],18,'源头供应商：参展团队、技术论坛、资料沟通'),
 9:([58,149,69],11,'环保降本选型：产品介绍、双碳交流、展台洽谈'),
 10:([286,87,22],19,'磷化与硅晶：现场样品交流、技术培训、工艺讨论'),
 11:([145,91,39],15,'药剂选型：行业参展、技术培训、资料沟通'),
 12:([118,89,72],19,'转化膜选型：行业展台、工艺知识培训、展会交流'),
 13:([52,90,111],21,'路线对比：企业展台、技术培训、行业沟通'),
 14:([207,86,38],16,'铝材供应商：海外展台、处理与涂装培训、方案沟通'),
 15:([232,92,57],12,'药剂与交付：涂装峰会交流、技术培训、现场讲解'),
 16:([167,152,164],12,'环保路线：双碳峰会、绿色制造分享、行业交流'),
 17:([64,223,162],19,'上海供应商：展台、华理论坛技术分享、行业交流'),
 18:([48,158,50],20,'厂家选择：展台全景、双碳产业交流、现场沟通'),
 19:([144,235,68],12,'药剂环保降本：参展讨论、双碳产业交流、展会洽谈'),
 20:([55,106,32],19,'钢铁前处理：产品展示、技术培训、方案交流'),
 21:([112,216,211],12,'药剂供应商：技术大会、华理论坛、海外展台沟通'),
 22:([202,241,165],49,'工艺与服务：转化膜行业交流、双碳技术分享、行业沟通'),
}


def caption(index):
    if index in (10,22):return 'APS 汽车零部件表面技术大会 · 展台交流现场'
    if index in (39,38,32):return '布达佩斯参展 · 现场交流剪影'
    if index in (48,49,51,52,53,54,55,56,57,58,50):return '2025 中国国际表面处理展 · 和拓展台交流现场'
    if index in (64,69,72,68):return '维也纳参展 · 展台与交流现场'
    if index in (86,87,89,90,91,92,93,102,105,106):return '崇明东滩 · 金属表面处理及涂装技术培训现场'
    if index in (111,112,113,117,118):return '第 3 届 EIC 三电与储能技术大会 · 现场交流'
    if index in (138,144,145):return '日本展参展 · 展会现场纪实'
    if index in (149,152,157,158,170):return '双碳经济行业峰会 · 现场分享'
    if index in (161,162,164,165,167):return '双碳经济行业峰会 · 行业交流现场'
    if index in (173,179):return '上海之帆经贸巡展泰国曼谷站 · 展台交流'
    if index==197:return '中国表面工程协会涂装分会 2024 会员代表大会 · 技术分享'
    if index in (201,202):return '中国表面工程协会转化膜专委会第七届会员大会 · 行业交流'
    if index in (207,208,211):return '上海之帆经贸巡展越南胡志明站 · 展台交流'
    if index in (215,216,223):return '华理“新化工、新流体、新机遇”产业论坛 · 技术分享现场'
    if index in (230,232,233):return '材涂联动高性能涂装峰会 · 现场纪实'
    if index in (235,241):return '绿色双碳产业联盟活动 · 现场分享'
    if index==286:return '中国国际表面处理展 · 和拓展台交流'
    raise ValueError(index)


def apply():
    import server as s
    from sample_review import layout_current,require_current_sources
    rows=json.loads((ROOT/'.runtime/scene-batch-before.json').read_text(encoding='utf-8'))
    photos=json.loads((ROOT/'.runtime/scene-photo-candidates.json').read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True)
    manifest=[]
    with s.db() as c:
        assert s.project(c,PID)['website'].rstrip('/')=='https://www.heroto.com.cn'
        baseline={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        # Validate all articles first, then apply one transaction.
        pending=[]
        for idx,(choices,middle,rationale) in PLAN.items():
            expected=rows[idx];rid=expected['id'];assert rid!=SAMPLE
            row=s.resource(c,PID,rid,'content')
            assert row['revision']==expected['revision'] and row['layout']==expected['layout'] and row['body']==expected['body']
            assert row['status']=='pending' and layout_current(row) and len(row['layout']['figures'])==4
            require_current_sources(vars(s),c,PID,row)
            assert not any(p.get('content_id')==rid and p['status']!='cancelled' for p in s.items(c,PID,'publication'))
            assert not any(j.get('status') in ('queued','running') and (j.get('content_id')==rid or j.get('payload',{}).get('content_id')==rid) for j in s.items(c,PID,'execution'))
            opening=0 if row['layout']['blocks'][0].get('text','')==row['title'] else 1
            ending=max(j for j,b in enumerate(row['layout']['blocks']) if b.get('text','').strip() and not b['text'].lstrip().startswith('#'))
            positions=[opening,middle,ending]
            assert 0<=opening<middle<ending
            assert middle not in [f['after'] for f in row['layout']['figures']],(idx,middle)
            selected=[]
            for number,pos in zip(choices,positions):
                a=s.resource(c,PID,photos[number]['id'],'asset')
                path=ROOT/'.runtime/assets'/PID/a['storage_key']
                assert hashlib.sha256(path.read_bytes()).hexdigest()==a['sha256']
                with Image.open(path) as im:
                    assert im.width>=700 and im.height>=400,(number,im.size)
                    im.verify()
                assert a.get('source_refs') and a.get('related_knowledge_ids'),number
                origins=[]
                for kid in a['related_knowledge_ids']:
                    doc=s.resource(c,PID,kid,'knowledge')
                    origins.append({'id':kid,'version':doc['version'],'title':doc['title']})
                selected.append({'asset_id':a['id'],'sha256':a['sha256'],'storage_key':a['storage_key'],'after':pos,'caption':caption(number),'source_refs':a['source_refs'],'source_documents':origins,'nearby_text':row['layout']['blocks'][pos].get('text','')})
            assert len({a['sha256'] for a in selected})==3
            pending.append((row,selected,rationale))
        for row,selected,rationale in pending:
            original=copy.deepcopy(row)
            row.setdefault('history',[]).append({k:copy.deepcopy(row.get(k)) for k in ('revision','title','body','channels','status','layout','platform_payloads')})
            for a in selected:row['layout']['figures'].append({k:a[k] for k in ('asset_id','after','caption')}|{'type':'scene_photo'})
            row['layout']['scene_photo_batch']={'version':1,'rationale':rationale,'sources':selected}
            for variant in row.get('platform_payloads',{}).values():
                variant['attachment_ids']=list(dict.fromkeys(variant.get('attachment_ids',[])+[a['asset_id'] for a in selected]))
            row.update(revision=row['revision']+1,approved_revision=None,review_note='',preparation_status='封面、4张价值图与3张实景照片 · 待客户审阅')
            row.pop('quality',None)
            row.setdefault('review_notes',[]).append('新增3张公众号实景照片：开篇、中段和结尾。图注按实际活动标明来源，活动照片不代表正文案例或性能数据的检测证据。')
            s.put(c,PID,'content',row,row['id'])
            for key in ('body','title','sources','channels'):assert row[key]==original[key]
            assert row['layout']['cover_id']==original['layout']['cover_id'] and row['layout']['blocks']==original['layout']['blocks']
            assert row['layout']['figures'][:4]==original['layout']['figures']
            manifest.append({'id':row['id'],'title':row['title'],'revision':row['revision'],'rationale':rationale,'photos':selected})
        after={r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        assert {key for key in baseline if baseline[key]!=after[key]}=={m['id'] for m in manifest}
        assert len(manifest)==22
        s.event(c,PID,'local-design-assistant','其余文章搭配公众号实景照片','22篇新增66个实景图位置；封面、原文、价值图与旧版保留；未发布')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def export():
    import server as s
    from sample_review import render_reader,embedded_asset_url,require_current_sources
    from preview_images import render_images
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    ids=[SAMPLE]+[m['id'] for m in manifest]
    summaries=[]
    for idx,rid in enumerate(ids,1):
        with s.db() as c:
            row=s.resource(c,PID,rid,'content');require_current_sources(vars(s),c,PID,row)
            document=render_reader(s.project(c,PID),row,embedded_asset_url(vars(s),c,PID))
            assert document.count('<img ')==8
            assert all(x not in document for x in ('<script','<aside>'))
            assert not re.search(r'(?:src|href)=[\"\']/api/',document)
        name=f'{idx:02d}-'+re.sub(r'[<>:"/\\|?*]','',row['title'])[:65]+f'-v{row["revision"]}'
        saved_html=OUT/(name+'.html');saved_png=OUT/(name+'.png')
        current=saved_html.exists() and saved_html.read_text(encoding='utf-8')==document
        raw=saved_png.read_bytes() if current and saved_png.exists() else render_images(document)
        saved_html.write_text(document,encoding='utf-8')
        with Image.open(io.BytesIO(raw)) as im:
            assert im.width==860 and im.height>1000
            dims=im.size;im.verify()
        (OUT/(name+'.png')).write_bytes(raw)
        summaries.append({'id':rid,'revision':row['revision'],'title':row['title'],'file':name+'.png','dimensions':dims,'images':8})
        print(f'Exported {idx}/23: {rid}',flush=True)
    for extension,label in [('png','长图'),('html','HTML')]:
        with zipfile.ZipFile(ROOT/f'outputs/和拓-23篇实景图文预览-{label}.zip','w',zipfile.ZIP_DEFLATED) as pack:
            for summary in summaries:
                path=OUT/Path(summary['file']).with_suffix('.'+extension)
                pack.write(path,path.name)
            pack.writestr('阅读说明.txt','本批为待客户审核稿。每篇包含封面、4张价值图、3张实景照片。\n实景照片图注为实际活动，不能据此认定正文案例或性能参数已核准。\n请按文章标题和版本号反馈修改意见。PNG可作为图片发送，HTML需浏览器打开。\n')
    (OUT/'verification.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    # Editorial overview uses full uncropped photos, not synthetic scenes.
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
    for start in range(0,len(manifest),6):
        subset=manifest[start:start+6];sheet=Image.new('RGB',(1350,len(subset)*310),'#edf2f3');d=ImageDraw.Draw(sheet)
        for n,m in enumerate(subset):
            y=n*310;d.text((15,y+5),m['title'][:58],fill='#18383c',font=font)
            for j,a in enumerate(m['photos']):
                im=Image.open(ROOT/'.runtime/assets'/PID/a['storage_key']).convert('RGB');im.thumbnail((425,240))
                sheet.paste(im,(15+j*445,y+40));d.text((15+j*445,y+278),['开篇','中段','结尾'][j]+' · '+a['caption'][:20],fill='#345456',font=font)
        sheet.save(OUT/f'搭配总览-{start+1:02d}.jpg',quality=90)
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>和拓实景图文预览</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;line-height:2}a{display:block}</style><h1>和拓 · 23篇实景图文预览</h1><p>客户待审版，每篇3张实景照片；点击阅读或打开对应长图。</p>'+''.join('<p>'+html.escape(m['title'])+'<a href="'+html.escape(str(Path(m['file']).with_suffix('.html')),quote=True)+'">阅读图文</a><a href="'+html.escape(m['file'],quote=True)+'">打开长图</a></p>' for m in summaries),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if args.export:export()
    else:print('Updated',len(apply()),'articles')
