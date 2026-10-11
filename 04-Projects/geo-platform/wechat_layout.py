"""Tenant-scoped saved WeChat layout and reusable, locally hosted brand template."""
import hashlib
import copy
import html
import json
import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup, Comment
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

import source_import
import sample_review as review

TAGS = set('section div p span strong b em i u s br hr img a blockquote ul ol li table tbody thead tr td th h1 h2 h3 h4'.split())
CSS = set('color background-color font-family font-size font-weight font-style line-height letter-spacing text-align text-indent text-decoration margin margin-top margin-bottom margin-left margin-right padding padding-top padding-bottom padding-left padding-right border border-top border-bottom border-left border-right border-radius border-color border-width border-style border-collapse width max-width min-width height max-height display vertical-align box-sizing word-break overflow-wrap white-space'.split())


def clean_style(value):
    out = []
    for declaration in value.split(';'):
        key, _, val = declaration.partition(':')
        key, val = key.strip().lower(), val.strip()
        if key in CSS and not re.search(r'url|expression|[\\@<>\x00-\x1f]|/\*', val, re.I):
            out.append(key + ':' + val)
    return ';'.join(out)


def image_url(value):
    import wechat_sync as wx
    try:
        p = urlsplit(value)
        original = urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))
    except (ValueError, TypeError):
        raise HTTPException(409, '样稿图片地址无效') from None
    if not wx.valid_image_url(original):
        raise HTTPException(409, '样稿包含非微信官方图片地址，未导入')
    return urlunsplit(('https', p.netloc, p.path, p.query, ''))


def sanitize(raw):
    if not isinstance(raw, str) or not raw or len(raw) > 500000:
        raise HTTPException(409, '公众号正文为空或过大')
    soup = BeautifulSoup(raw, 'html.parser')
    warnings = []
    for comment in soup.find_all(string=lambda x: isinstance(x, Comment)): comment.extract()
    for el in list(soup.find_all()):
        if el.name is None: continue
        if el.name == 'mp-common-videosnap':
            notice = soup.new_tag('p')
            notice.string = '视频号卡片请在公众号中查看；后续文章需按内容另行插入。'
            el.replace_with(notice)
            warnings.append('视频号卡片未作为通用模板复用')
            continue
        if el.name in ('script', 'style', 'iframe', 'object', 'embed', 'svg', 'math', 'form', 'input', 'button', 'mp-style-type'):
            el.decompose(); continue
        if el.name not in TAGS:
            el.unwrap(); continue
        attrs = {}
        style = clean_style(el.get('style', ''))
        if style: attrs['style'] = style
        if el.name == 'img':
            src = el.get('data-src') or el.get('src')
            if not src: el.decompose(); continue
            attrs.update(src=image_url(src), alt=el.get('alt', ''))
            attrs['style'] = style + ';max-width:100%;height:auto'
        if el.name == 'a':
            try:
                p = urlsplit(el.get('href', ''))
                if p.scheme == 'https' and p.hostname == 'mp.weixin.qq.com' and not p.username and not p.password and p.port is None:
                    attrs['href'] = el['href']
            except ValueError: pass
        if el.name in ('td', 'th'):
            for key in ('colspan', 'rowspan'):
                if str(el.get(key, '')).isdigit(): attrs[key] = str(min(int(el[key]), 30))
        el.attrs = attrs
    return soup, list(dict.fromkeys(warnings))


def fetch_image(url):
    url = image_url(url)
    try:
        with httpx.Client(timeout=35, trust_env=False, follow_redirects=False) as client:
            with client.stream('GET', url) as response:
                if response.status_code != 200: raise ValueError()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 10 * 1024 * 1024: raise ValueError()
        review.preview_image_format(bytes(data))
        return bytes(data)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(409, '样稿图片下载失败，未保存模板，请稍后重试') from None


def profile(body):
    soup = BeautifulSoup(body, 'html.parser')
    root = soup.find('section')
    if not root: raise HTTPException(409, '样稿缺少排版容器')
    children = list(root.find_all(recursive=False))
    heading = next((p for p in children if re.match(r'^NO\.\s*1\b', p.get_text().strip(), re.I)), None)
    if not heading: raise HTTPException(409, '样稿缺少 NO.1 章节样式，未设置默认模板')
    heading_copy = BeautifulSoup(str(heading), 'html.parser')
    texts = list(heading_copy.find_all(string=True))
    for text in texts:
        if re.match(r'^NO\.\s*1\s*$', str(text).strip(), re.I): text.replace_with('{{number}}\u00a0')
        elif str(text).strip(): text.replace_with('{{heading}}')
    if str(heading_copy).count('{{heading}}') != 1 or str(heading_copy).count('{{number}}') != 1:
        raise HTTPException(409, '章节样式无法安全拆分，请核对样稿')
    caption = next((p.get('style', '') for p in children if p.name == 'p' and 'font-size:12px' in p.get('style', '')), '')
    paragraph = next((p.get('style', '') for p in children if p.name == 'p' and 'font-size:16px' in p.get('style', '')), '')
    # Header ends before the video's placeholder or the first article illustration/caption.
    first_caption = next((i for i,p in enumerate(children) if p.name == 'p' and p.get('style') == caption), 0)
    header_end = max(0, first_caption - 1)
    header = ''.join(str(p) for p in children[:header_end] if '视频号卡片' not in p.get_text())
    footer_start = next((i for i,p in enumerate(children) if '有限公司' in p.get_text() and '是一家' in p.get_text()), len(children))
    if footer_start < len(children) and footer_start and children[footer_start-1].find('img'): footer_start -= 1
    return {'wrapper_style': root.get('style', ''), 'heading_html': str(heading_copy),
            'paragraph_style': paragraph, 'caption_style': caption,
            'header_html': header, 'footer_html': ''.join(str(p) for p in children[footer_start:])}


def selected(g, c, pid):
    import wechat_sync as wx
    cfg = wx.config(c, g, pid) or {}
    return next((t for t in g['items'](c, pid, 'wechat_layout') if t.get('default') and t['appid'] == cfg.get('appid')), None)


def status(template):
    if not template: return None
    return {k: template.get(k) for k in ('id', 'name', 'version', 'source_content_id', 'source_revision', 'imported_at', 'warnings', 'image_count')}


def is_source(template, content):
    return bool(template and template['source_content_id'] == content['id'] and template['source_revision'] == content['revision']
                and template['local_body_sha256'] == hashlib.sha256(content['body'].encode()).hexdigest())


def resolve_fragment(fragment, resolve):
    soup = BeautifulSoup(fragment, 'html.parser')
    for img in soup.find_all('img'):
        aid = img.get('src', '').removeprefix('asset:')
        img['src'] = resolve(aid, -1, img.get('alt', ''))
    return image_link_markup(str(soup))


def image_link_markup(fragment):
    """Restore native WeChat image-link metadata using the resolved image URL."""
    soup = BeautifulSoup(fragment, 'html.parser')
    for anchor in soup.select('a[href]'):
        image = anchor.find('img')
        if not image: continue
        try:
            url = urlsplit(anchor['href'])
            if url.scheme != 'https' or url.hostname != 'mp.weixin.qq.com' or url.username or url.password or url.port is not None:
                continue
        except ValueError:
            continue
        anchor.attrs.update({'linktype': 'image', 'tab': 'innerlink', 'data-itemshowtype': '0',
                             'target': '_blank', 'data-linktype': '1',
                             'imgurl': image.get('data-src') or image.get('src', '')})
    return str(soup)


def render(template, content, resolve, render_basic):
    if is_source(template, content):
        return resolve_fragment(template['body_html'], resolve)
    p = template['profile']
    body = BeautifulSoup(render_basic(content, resolve), 'html.parser')
    number = 0
    for el in list(body.section.find_all('p', recursive=False)):
        text = el.get_text()
        if 'font-size:19px' in el.get('style', ''):
            number += 1
            text = re.sub(r'^(?:NO\.\s*\d+|案例[一二三四五六七八九十0-9]+[：:]|[一二三四五六七八九十百]+[、．.]|\d+[、．.])\s*', '', text, flags=re.I)
            replacement = p['heading_html'].replace('{{number}}', 'NO.' + str(number)).replace('{{heading}}', html.escape(text))
            el.replace_with(BeautifulSoup(replacement, 'html.parser'))
        elif not el.find('img'):
            el['style'] = p['caption_style'] if 'font-size:12px' in el.get('style', '') else p['paragraph_style']
    return '<section style="' + html.escape(p['wrapper_style'], quote=True) + '">' + resolve_fragment(p['header_html'], resolve) + body.section.decode_contents() + resolve_fragment(p['footer_html'], resolve) + '</section>'


def apply_to_content(g, c, pid, content, template):
    """Materialize one article's layout for the workspace, reader and WeChat export."""
    import wechat_export
    review.require_current_layout(content)
    review.require_current_sources(g, c, pid, content)
    if content['status'] == 'generating': raise HTTPException(409, '文章正在生成')
    checked = {}
    def resolve(aid, index, caption):
        if aid not in checked:
            if len(checked) >= 40: raise HTTPException(409, '文章图片超过40张')
            raw, snapshot = review.preview_asset_bytes(g, c, pid, aid)
            review.preview_image_format(raw); checked[aid] = snapshot
        return 'asset:' + aid
    body = render(template, content, resolve, wechat_export.render_body)
    review.require_unchanged_preview_assets(g, c, pid, checked)
    updated = copy.deepcopy(content)
    updated.setdefault('history', []).append({k: copy.deepcopy(content[k]) for k in ('revision', 'title', 'body', 'channels', 'status', 'layout')})
    updated.update(revision=content['revision']+1, approved_revision=None, review_note='', status='pending' if content['status']=='pending' else 'draft')
    for key in ('quality', 'platform_payloads', 'approved_at', 'approved_by'): updated.pop(key, None)
    updated['layout'].update(wechat_html=body, wechat_template_version=template['version'], wechat_template_id=template['id'],
                             body_sha256=hashlib.sha256(updated['body'].encode()).hexdigest(),
                             title_sha256=hashlib.sha256(updated['title'].encode()).hexdigest(), outdated=False)
    g['put'](c, pid, 'content', updated, content['id'])
    for pub in g['items'](c, pid, 'publication'):
        if pub['content_id']==content['id'] and pub['status'] in ('awaiting_connector','wp_draft'):
            pub['status']='cancelled'; g['put'](c,pid,'publication',pub,pub['id'])
    return updated


class ImportLayout(BaseModel):
    revision: int = Field(ge=1)
    appid: str
    binding_version: int = Field(ge=1)
    make_default: bool = False


def register(g):
    import wechat_sync as wx

    @g['app'].post('/api/projects/{pid}/contents/{rid}/wechat-draft/{jid}/import-layout')
    def import_layout(pid: str, rid: str, jid: str, body: ImportLayout, request: Request):
        with wx.locked(g, pid):
            def check(c):
                actor, _ = g['scope'](c, request, pid, ['owner'] if body.make_default else ['owner', 'editor'])
                cfg = wx.config(c, g, pid)
                content = g['resource'](c, pid, rid, 'content')
                job = g['resource'](c, pid, jid, 'wechat_draft')
                if not cfg or cfg['appid'] != body.appid or cfg['version'] != body.binding_version or job['appid'] != body.appid:
                    raise HTTPException(409, '目标公众号已变化，请重新打开')
                if job['content_id'] != rid or not job.get('media_id'): raise HTTPException(409, '缺少此文章的微信草稿编号')
                if content['revision'] != body.revision: raise HTTPException(409, '本地文章已变化，请重新打开')
                return actor, cfg, content, job
            with g['db']() as c: actor, cfg, content, job = check(c)
            try:
                remote = wx.call('/cgi-bin/draft/get', wx.access_token(g, pid, cfg), {'media_id': job['media_id']})
            except wx.WechatError as exc: raise HTTPException(409, str(exc)) from None
            if len(remote.get('news_item', [])) != 1: raise HTTPException(409, '目前只支持单篇草稿排版回同步')
            article = remote['news_item'][0]
            soup, warnings = sanitize(article.get('content'))
            source_hash = hashlib.sha256(json.dumps(article, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            urls = list(dict.fromkeys(img['src'] for img in soup.find_all('img')))
            if len(urls) > 40: raise HTTPException(409, '样稿图片超过40张，请精简后再导入')
            images = {}; total = 0
            for url in urls:
                raw = fetch_image(url); total += len(raw)
                if total > 40 * 1024 * 1024: raise HTTPException(409, '样稿配图总量超过40MB')
                images[url] = raw
            # Validate profile before any persistent asset writes.
            profile(str(soup))
            with g['db']() as c:
                actor, _, current, _ = check(c)
                if current['body'] != content['body']: raise HTTPException(409, '本地正文已变化')
                prior = g['items'](c, pid, 'wechat_layout')
                same = next((t for t in prior if t['source_content_id'] == rid and t['source_revision'] == body.revision and t['source_sha256'] == source_hash and t['appid'] == body.appid and t.get('default') == body.make_default), None)
                if same: return status(same)
                mapping = {}
                for index, (url, raw) in enumerate(images.items()):
                    _, ext = review.preview_image_format(raw)
                    if ext == 'gif':
                        # Preserve animated originals in the existing asset model.
                        source_import.MIMES.setdefault('.gif', 'image/gif')
                    mapping[url] = source_import.store_asset(g, c, pid, raw, f'公众号排版样稿-{index+1}.{ext}', {'wechat_media_id': job['media_id'], 'url': url}, '图片')
                for img in soup.find_all('img'): img['src'] = 'asset:' + mapping[img['src']]
                value = {'name': '公众号默认排版 · NO.章节', 'version': max((x['version'] for x in prior), default=0)+1,
                         'appid': body.appid, 'default': body.make_default, 'source_content_id': rid, 'source_revision': body.revision,
                         'source_sha256': source_hash, 'local_body_sha256': hashlib.sha256(content['body'].encode()).hexdigest(),
                         'source_media_id': job['media_id'], 'title': article.get('title', content['title']),
                         'author': article.get('author', ''), 'digest': article.get('digest', ''),
                         'body_html': str(soup), 'profile': profile(str(soup)), 'image_count': len(urls),
                         'imported_at': g['now'](), 'warnings': warnings, 'actor': actor['user_id']}
                if body.make_default:
                    for old in prior:
                        if old.get('default') and old['appid'] == body.appid:
                            old['default'] = False; g['put'](c, pid, 'wechat_layout', old, old['id'])
                tid = g['put'](c, pid, 'wechat_layout', value)
                g['event'](c, pid, actor['user_id'], '回同步公众号排版并设置默认模板' if body.make_default else '回同步公众号排版', rid)
                return status({'id': tid, **value})
