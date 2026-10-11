"""Restore original WeChat image-link metadata in the 22 authorized drafts.

Existing media IDs only; protect first article, compare before updating, never publish.
"""
from sync_hetuo_batch85 import *

if __name__ == '__main__':
    plan = preflight()
    path = ROOT / 'iteration85-native-links.json'
    receipts = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    targets = [SECOND] + [x['id'] for x in plan['items']]
    for i, rid in enumerate(targets, 1):
        previous = next((x for x in receipts if x['id'] == rid), None)
        if previous:
            assert previous['status'] == 'verified', 'Uncertain update requires read-only reconciliation'
            continue
        with s.db() as c:
            cfg, template = guard(c, plan)
            job = next(x for x in s.items(c, PID, 'wechat_draft') if x['content_id'] == rid and x['status'] == 'synced' and x['appid'] == cfg['appid'])
            content = s.resource(c, PID, rid, 'content')
        token = wx.access_token(G, PID, cfg)
        remote = wx.call('/cgi-bin/draft/get', token, {'media_id': job['media_id']})
        assert wx.draft_matches(remote, job['expected']), 'Remote manually changed: do not overwrite'
        article = remote['news_item'][0]
        body = layout.image_link_markup(article['content'])
        before = wx.article_signature(article)
        assert wx.article_signature({**article, 'content': body}) == before, 'Content changed beyond metadata'
        anchors = BeautifulSoup(body, 'html.parser').select('a[linktype="image"][data-linktype="1"]')
        assert len(anchors) == 7 and all(a['imgurl'] == (a.img.get('data-src') or a.img['src']) for a in anchors)
        entry = dict(id=rid, media_id=job['media_id'], status='sending', title=article['title'])
        receipts.append(entry)
        path.write_text(json.dumps(receipts, ensure_ascii=False, indent=2), encoding='utf-8')
        allowed = ('title','author','digest','content','content_source_url','thumb_media_id','show_cover_pic','need_open_comment','only_fans_can_comment')
        outgoing = {k: article[k] for k in allowed if k in article}
        outgoing['content'] = body
        wx.call('/cgi-bin/draft/update', token, {'media_id': job['media_id'], 'index': 0, 'articles': outgoing})
        actual = wx.call('/cgi-bin/draft/get', token, {'media_id': job['media_id']})
        assert wx.draft_matches(actual, before), 'Readback content differs'
        anchors = BeautifulSoup(actual['news_item'][0]['content'], 'html.parser').select('a[linktype="image"][data-linktype="1"]')
        assert len(anchors) == 7 and all(a.get('tab') == 'innerlink' and wx.valid_image_url(a.get('imgurl','')) for a in anchors), 'Native metadata not retained'
        with s.db() as c:
            guard(c,plan)
            current = s.resource(c,PID,rid,'content')
            assert sha(current) == sha(content), 'Local changed'
            prepared, assets, manifest = export.prepare(G,c,PID,current)
            job.update(expected=wx.article_signature(actual['news_item'][0]), native_image_links=True, synced_at=s.now(),
                       fingerprint=hashlib.sha256(json.dumps([cfg['appid'],rid,current['revision'],prepared,manifest],sort_keys=True,ensure_ascii=False).encode()).hexdigest())
            s.put(c,PID,'wechat_draft',job,job['id'])
            s.event(c,PID,plan['actor'],'补齐微信原生图片链接标记',rid+' · 7个链接 · 原草稿原位更新')
        entry.update(status='verified',links=7,body_and_images_unchanged=True)
        path.write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
        print('VERIFIED',i,'/22',article['title'],flush=True)
