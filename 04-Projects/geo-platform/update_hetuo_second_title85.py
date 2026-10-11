"""Authorized title-only update of the existing second draft; never creates a draft."""
import copy
import json
from sync_hetuo_batch85 import *

if __name__ == '__main__':
    plan = preflight()
    receipt = ROOT / 'iteration85-second-title.json'
    assert not receipt.exists(), 'Existing update receipt: inspect before retry'
    with s.db() as c:
        cfg, template = guard(c, plan)
        content = s.resource(c, PID, SECOND, 'content')
        job = next(x for x in s.items(c, PID, 'wechat_draft') if x['content_id'] == SECOND and x['status'] == 'synced')
        first_job = next(x for x in s.items(c, PID, 'wechat_draft') if x['content_id'] == FIRST and x['status'] == 'synced')
    token = wx.access_token(G, PID, cfg)
    first_remote = wx.call('/cgi-bin/draft/get', token, {'media_id': first_job['media_id']})
    remote = wx.call('/cgi-bin/draft/get', token, {'media_id': job['media_id']})
    assert wx.draft_matches(remote, job['expected']), 'Second draft manually changed; do not overwrite'
    old = remote['news_item'][0]
    title = clean_title(old['title'])
    assert title != old['title'] and title == clean_title(content['title'])
    expected = wx.article_signature({**old, 'title': title})
    assert len(expected['links']) == 7
    data = dict(status='sending', content_id=SECOND, media_id=job['media_id'], old_title=old['title'], title=title, expected=expected, first_remote_signature=wx.article_signature(first_remote['news_item'][0]), published=False)
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    # Full editable article fields from the just-read draft; only title differs.
    allowed = ('title', 'author', 'digest', 'content', 'content_source_url', 'thumb_media_id', 'show_cover_pic', 'need_open_comment', 'only_fans_can_comment')
    article = {k: old[k] for k in allowed if k in old}
    article['title'] = title
    wx.call('/cgi-bin/draft/update', token, {'media_id': job['media_id'], 'index': 0, 'articles': article})
    actual = wx.call('/cgi-bin/draft/get', token, {'media_id': job['media_id']})
    assert wx.draft_matches(actual, expected), 'Title update readback mismatch'
    with s.db() as c:
        guard(c, plan)
        current = s.resource(c, PID, SECOND, 'content')
        assert sha(current) == sha(content), 'Local article changed'
        updated = copy.deepcopy(current)
        updated.setdefault('history', []).append({k: copy.deepcopy(current[k]) for k in ('revision', 'title', 'body', 'channels', 'status', 'layout')})
        strip_local_title(updated)
        updated.update(revision=current['revision'] + 1, approved_revision=None, review_note='')
        for key in ('quality', 'platform_payloads', 'approved_at', 'approved_by'): updated.pop(key, None)
        s.put(c, PID, 'content', updated, SECOND)
        body, assets, manifest = export.prepare(G, c, PID, updated)
        job.update(revision=updated['revision'], expected=expected, synced_at=s.now(), title_updated=True,
                   fingerprint=hashlib.sha256(json.dumps([cfg['appid'], SECOND, updated['revision'], body, manifest],sort_keys=True,ensure_ascii=False).encode()).hexdigest())
        s.put(c, PID, 'wechat_draft', job, job['id'])
        s.event(c, PID, plan['actor'], '去除第二篇公众号草稿标题序号', SECOND + ' · 原草稿原位更新 · 正文图片链接不变')
    data.update(status='synced', revision=updated['revision'], body_images_links_unchanged=True)
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: data[k] for k in ('status','title','revision','body_images_links_unchanged')}, ensure_ascii=False))
