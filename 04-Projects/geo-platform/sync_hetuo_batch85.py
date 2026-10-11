"""One-off, user-authorized 21-article draft delivery. Never publishes.

Run without arguments for read-only preflight; --run resumes the pinned manifest.
Uses the configured tenant connector; does not create sessions or alter permissions.
"""
import copy
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import server as s
import wechat_layout as layout
import wechat_export as export
import wechat_sync as wx

sys.stdout.reconfigure(encoding='utf-8')
PID = 'a46fb911b04fbf0b783c7bf5'
FIRST = '9c8fd4efd0f7de9f21b0c97a'
SECOND = '382c69d078091f1527739361'
G = vars(s)
ROOT = s.ROOT / 'outputs'
PLAN = ROOT / 'iteration85-batch-plan.json'
RESULT = ROOT / 'iteration85-batch-result.json'

def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def clean_title(value):
    return re.sub(r'^\s*\d{1,2}[、．.]\s*', '', value, count=1)

def guard(c, plan):
    member = c.execute('SELECT role FROM members WHERE project_id=? AND user_id=?', (PID, plan['actor'])).fetchone()
    assert member and member['role'] in ('owner', 'editor'), 'Actor no longer authorized'
    cfg = wx.config(c, G, PID)
    assert cfg['appid'] == plan['appid'] and cfg['version'] == plan['binding_version'] and cfg['status'] == 'verified_read', 'Binding changed'
    template = layout.selected(G, c, PID)
    assert template['id'] == plan['template_id'] and template['version'] == 3, 'Template changed'
    assert sha(s.resource(c, PID, FIRST, 'content')) == plan['first_sha256'], 'Protected first article changed'
    return cfg, template

def preflight():
    if PLAN.exists():
        plan = json.loads(PLAN.read_text(encoding='utf-8'))
        with s.db() as c: guard(c, plan)
        return plan
    with s.db() as c:
        records = s.items(c, PID, 'wechat_draft')
        second_job = next(x for x in records if x['content_id'] == SECOND and x['status'] == 'synced')
        cfg, template = wx.config(c, G, PID), layout.selected(G, c, PID)
        rows = [x for x in reversed(s.items(c, PID, 'content')) if x['id'] not in (FIRST, SECOND) and x.get('layout') and re.match(r'^\d+[、．.]', x['title'])]
        assert len(rows) == 21, 'Expected exactly 21 articles'
        plan = dict(project_id=PID, actor=second_job['actor'], appid=cfg['appid'], binding_version=cfg['version'], template_id=template['id'], first_sha256=sha(s.resource(c, PID, FIRST, 'content')), items=[])
        guard(c, plan)
        expected_links = [a['href'] for a in BeautifulSoup(template['profile']['footer_html'], 'html.parser').select('a[href]')]
        assert len(expected_links) == 7
        for content in rows:
            assert not any(x['content_id'] == content['id'] and x['status'] != 'failed' for x in records), 'Existing draft requires review'
            body, assets, manifest = export.prepare(G, c, PID, content)
            soup = BeautifulSoup(body, 'html.parser')
            assert manifest['cover'] and manifest['template_version'] == 3
            assert [a['href'] for a in soup.select('a[href]')] == expected_links
            plan['items'].append(dict(id=content['id'], before_revision=content['revision'], before_sha256=sha(content), title=clean_title(content['title']), images=len(soup.select('img')), links=7))
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    return plan

def strip_local_title(content):
    old, new = content['title'], clean_title(content['title'])
    content['title'] = new
    if content['body'].startswith(old): content['body'] = new + content['body'][len(old):]
    for block in content.get('layout', {}).get('blocks', []):
        if block.get('text') == old: block['text'] = new
    content['layout'].update(title_sha256=hashlib.sha256(new.encode()).hexdigest(), body_sha256=hashlib.sha256(content['body'].encode()).hexdigest())

def run_item(plan, item):
    with wx.locked(G, PID):
        with s.db() as c:
            cfg, template = guard(c, plan)
            content = s.resource(c, PID, item['id'], 'content')
            prior = [x for x in s.items(c, PID, 'wechat_draft') if x['content_id'] == item['id'] and x['appid'] == cfg['appid']]
            synced = next((x for x in prior if x['status'] == 'synced'), None)
            if synced:
                assert synced.get('batch') == 85
                return dict(id=item['id'], title=content['title'], status='synced', media_id=synced['media_id'], revision=content['revision'], images=item['images'], links=7)
            assert not any(x['status'] != 'failed' for x in prior), 'Uncertain remote outcome: reconcile, never resend'
            if content['revision'] == item['before_revision']:
                assert sha(content) == item['before_sha256'], 'Article changed since preflight'
                content = layout.apply_to_content(G, c, PID, content, template)
                strip_local_title(content)
                s.put(c, PID, 'content', content, item['id'])
                s.event(c, PID, plan['actor'], '套用已确认公众号排版并去除标题序号', item['id'] + ' · batch85')
                content = s.resource(c, PID, item['id'], 'content')
            assert content['revision'] == item['before_revision'] + 1 and content['title'] == item['title']
            body, assets, manifest = export.prepare(G, c, PID, content)
            fingerprint = hashlib.sha256(json.dumps([cfg['appid'], item['id'], content['revision'], body, manifest], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            job = dict(content_id=item['id'], revision=content['revision'], fingerprint=fingerprint, appid=cfg['appid'], status='preparing', media_id='', error='', actor=plan['actor'], published=False, batch=85)
            jid = s.put(c, PID, 'wechat_draft', job)
        def save(**updates):
            job.update(updates)
            with s.db() as c: s.put(c, PID, 'wechat_draft', job, jid)
        def check():
            with s.db() as c:
                guard(c, plan)
                current = s.resource(c, PID, item['id'], 'content')
                assert sha(current) == sha(content), 'Article changed while uploading'
                check_body, check_assets, check_manifest = export.prepare(G, c, PID, current)
                assert check_body == body and check_manifest == manifest, 'Assets or layout changed'
        try:
            token = wx.access_token(G, PID, cfg)
            mapped = {}
            for path in dict.fromkeys(x['file'] for x in manifest['images'] if x['role'] == 'body'):
                check()
                asset = next(x for x in assets.values() if x['file'] == path)
                reply = wx.call('/cgi-bin/media/uploadimg', token, files={'media': wx.upload_image(asset)})
                assert wx.valid_image_url(reply.get('url', '')), 'Invalid uploaded image URL'
                mapped[path] = reply['url']
            check()
            cover = next(x for x in assets.values() if x['file'] == manifest['cover'])
            reply = wx.call('/cgi-bin/material/add_material?type=image', token, files={'media': wx.upload_image(cover, 'cover.' + cover['file'].split('.')[-1])})
            assert reply.get('media_id'), 'Missing cover receipt'
            outgoing = body
            for path, url in mapped.items(): outgoing = outgoing.replace('src="' + path + '"', 'src="' + html.escape(url, quote=True) + '"')
            article = dict(title=content['title'], content=outgoing, thumb_media_id=reply['media_id'], digest=wx.article_digest(content), author=template.get('author', ''), need_open_comment=0, only_fans_can_comment=0)
            check()
            save(status='sending', expected=wx.article_signature(article))
            reply = wx.call('/cgi-bin/draft/add', token, {'articles': [article]})
            assert reply.get('media_id'), 'Missing draft receipt'
            save(status='created', media_id=reply['media_id'])
            remote = wx.call('/cgi-bin/draft/get', token, {'media_id': reply['media_id']})
            assert wx.draft_matches(remote, job['expected']), 'Remote title/text/cover/images/links mismatch'
            check()
            save(status='synced', synced_at=s.now(), error='')
            with s.db() as c: s.event(c, PID, plan['actor'], '同步公众号草稿并回读核对', item['id'] + ' · batch85 · 未发布')
            return dict(id=item['id'], title=content['title'], status='synced', media_id=job['media_id'], revision=content['revision'], images=len(job['expected']['images']), links=len(job['expected']['links']))
        except Exception as exc:
            error = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
            save(status='needs_review' if job['status'] in ('sending', 'created') else 'failed', error=error)
            raise

if __name__ == '__main__':
    plan = preflight()
    print(json.dumps({'preflight': len(plan['items']), 'articles': plan['items']}, ensure_ascii=False), flush=True)
    if '--run' in sys.argv:
        results = []
        for i, item in enumerate(plan['items'], 1):
            print('START', i, item['title'], flush=True)
            result = run_item(plan, item)
            results.append(result)
            RESULT.write_text(json.dumps({'published': False, 'items': results}, ensure_ascii=False, indent=2), encoding='utf-8')
            print('DONE', i, json.dumps(result, ensure_ascii=False), flush=True)
        with s.db() as c: guard(c, plan)
        print('COMPLETE 21/21; first local record unchanged; no publish calls', flush=True)
