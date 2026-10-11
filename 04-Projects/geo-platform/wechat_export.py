"""Editable WeChat preparation copy. No upload, approval or publication side effects."""
import base64
import hashlib
import html
import io
import json
import re
import zipfile

from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response

import sample_review as review
import wechat_layout


def heading_indices(content):
    blocks = review.current_blocks(content)
    candidates = [(i, b.get('text','').strip()) for i,b in enumerate(blocks)
                  if b.get('text','').strip() != content['title'] and len(b.get('text','').strip()) < 140]
    explicit = {i for i,b in enumerate(blocks) if b.get('type') in ('heading','h2') and b.get('text','').strip() != content['title']}
    if explicit: return explicit
    for pattern in (r'^[一二三四五六七八九十百]+[、．.]', r'^案例[一二三四五六七八九十0-9]+[：:]',
                    r'^Q\d+[：:]', r'^(?:NO\.\s*\d+|\d{1,2}[、．.](?!\d))'):
        selected = {i for i,text in candidates if re.match(pattern,text,re.I)}
        if selected: return selected
    return set()


def render_body(content, image_url):
    """Keep text as text and each illustration at its source position."""
    esc = lambda value: html.escape(str(value), quote=True)
    segments = []
    primary_headings = heading_indices(content)
    for index, block in enumerate(review.current_blocks(content)):
        text = block.get('text', '').strip()
        if text and text != content['title']:
            if block.get('type') == 'table' and ' | ' in text:
                segments.append('<table style="border-collapse:collapse;width:100%;font-size:14px">' + ''.join(
                    '<tr>' + ''.join('<td style="border:1px solid #dbe1e7;padding:10px">' + esc(cell) + '</td>'
                                    for cell in row.split(' | ')) + '</tr>' for row in text.splitlines()) + '</table>')
            else:
                heading = index in primary_headings
                style = 'font-size:19px;font-weight:bold;color:#217d9c;margin:28px 0 16px' if heading else 'font-size:16px;margin:18px 0'
                segments.append('<p style="' + style + ';line-height:1.9;text-align:left;word-break:break-word">' + esc(text).replace('\n', '<br>') + '</p>')
        figures = [(aid, '') for aid in block.get('image_ids', [])]
        figures += [(f['asset_id'], f.get('caption', '')) for f in content.get('layout', {}).get('figures', []) if f['after'] == index]
        for aid, caption in figures:
            url = image_url(aid, index, caption)
            segments.append('<p style="margin:24px 0 8px"><img src="' + esc(url) + '" alt="' + esc(caption) + '" style="display:block;width:100%;height:auto"></p>')
            if caption:
                segments.append('<p style="font-size:12px;line-height:1.6;color:#78858a;margin:8px 0 24px">' + esc(caption) + '</p>')
    return '<section style="font-family:Arial,sans-serif;color:#202a35;font-size:16px;line-height:1.9">' + ''.join(segments) + '</section>'


def prepare(g, c, pid, content):
    review.require_current_layout(content)
    review.require_current_sources(g, c, pid, content)
    assets, snapshots, occurrences = {}, {}, []
    total = 0

    def resolve(aid, index, caption):
        nonlocal total
        if aid not in assets:
            if len(assets) >= 40:
                raise HTTPException(409, '公众号稿配图过多，请分篇整理')
            raw, snapshot = review.preview_asset_bytes(g, c, pid, aid)
            mime, extension = review.preview_image_format(raw)
            total += len(raw)
            if total > 40 * 1024 * 1024:
                raise HTTPException(409, '公众号稿图片总量过大，请压缩后重试')
            name = f'images/{len(assets):02d}.{extension}'
            assets[aid] = {'file': name, 'raw': raw, 'mime': mime}
            snapshots[aid] = snapshot
        occurrences.append({'file': assets[aid]['file'], 'role': 'cover' if index is None else 'body', 'after_block': index, 'caption': caption})
        return assets[aid]['file']

    cover_id = content.get('layout', {}).get('cover_id')
    cover = resolve(cover_id, None, '') if cover_id else None
    template = wechat_layout.selected(g, c, pid)
    if content.get('layout', {}).get('wechat_html'):
        body = wechat_layout.resolve_fragment(content['layout']['wechat_html'], resolve)
    else:
        body = wechat_layout.render(template, content, resolve, render_body) if template else render_body(content, resolve)
    review.require_unchanged_preview_assets(g, c, pid, snapshots)
    manifest = {'type': 'wechat_editable_preparation', 'synced': False, 'published': False,
                'content_id': content['id'], 'revision': content['revision'], 'title': content['title'],
                'cover': cover, 'images': occurrences,
                'assets': [{'file': assets[aid]['file'], 'sha256': snap['sha256']} for aid, snap in snapshots.items()]}
    manifest['template_version'] = template['version'] if template else 0
    if content.get('layout', {}).get('wechat_html'):
        manifest['template_version'] = content['layout']['wechat_template_version']
    manifest['template_name'] = template['name'] if template else ''
    manifest['imported_snapshot'] = wechat_layout.is_source(template, content)
    if manifest['imported_snapshot']: manifest['title'] = template['title']
    return body, assets, manifest


def document(title, body):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><body style="max-width:677px;margin:24px auto;padding:0 20px">' + body + '</body></html>'


def require_current_export(g, request, pid, rid, content, assets, template_version=None):
    """Recheck after serialization, which runs outside the initial DB scope."""
    with g['db']() as c:
        g['scope'](c, request, pid)
        current = g['resource'](c, pid, rid, 'content')
        if any(current.get(key) != content.get(key) for key in ('revision', 'title', 'body', 'layout', 'sources')):
            raise HTTPException(409, '生成期间文章或排版已变更，请重新打开公众号稿')
        review.require_current_layout(current)
        review.require_current_sources(g, c, pid, current)
        if template_version is not None:
            template = wechat_layout.selected(g, c, pid)
            if (template['version'] if template else 0) != template_version:
                raise HTTPException(409, '公众号排版模板已变化，请重新预览确认')
        for aid, asset in assets.items():
            try:
                raw, _ = review.preview_asset_bytes(g, c, pid, aid)
            except HTTPException as exc:
                if exc.status_code not in (404, 409):
                    raise
                raise HTTPException(409, '生成期间配图已变更或不可用，请重新打开公众号稿') from exc
            if hashlib.sha256(raw).digest() != hashlib.sha256(asset['raw']).digest():
                raise HTTPException(409, '生成期间配图已变更，请重新打开公众号稿')


def register(g):
    import wechat_sync
    wechat_sync.register(g)
    wechat_layout.register(g)
    @g['app'].get('/api/projects/{pid}/contents/{rid}/wechat-preview')
    def wechat_preview(pid: str, rid: str, request: Request, revision: int = Query(ge=1), download: bool = False):
        with g['db']() as c:
            g['scope'](c, request, pid)
            content = g['resource'](c, pid, rid, 'content')
            if content['revision'] != revision:
                raise HTTPException(409, '内容版本已更新，请返回文章重新打开公众号稿')
            body, assets, manifest = prepare(g, c, pid, content)
        display_title = manifest['title']
        headers = {'Cache-Control': 'no-store', 'X-Content-Revision': str(revision)}
        if download:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
                z.writestr('title.txt', display_title)
                z.writestr('body.html', body)
                z.writestr('article.html', document(display_title, body))
                z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
                z.writestr('README.txt', '这是文字与独立配图组成的公众号准备稿，不是整篇长图。\n标题见 title.txt，正文见 article.html，封面与配图位置见 manifest.json。\n本机图片需要上传到公众号后再插入正文；此压缩包不能直接上传成公众号草稿。\n尚未同步、审核或发布；需要在已登录的公众号编辑器或授权草稿接口完成导入并核对。')
                for asset in assets.values():
                    z.writestr(asset['file'], asset['raw'])
            headers['Content-Disposition'] = f'attachment; filename="wechat-article-{rid}-v{revision}.zip"'
            require_current_export(g, request, pid, rid, content, assets, manifest['template_version'])
            return Response(stream.getvalue(), media_type='application/zip', headers=headers)
        # Preview is self-contained; no local authenticated URLs are embedded in the copy.
        def embedded(path):
            asset = next(a for a in assets.values() if a['file'] == path)
            return 'data:' + asset['mime'] + ';base64,' + base64.b64encode(asset['raw']).decode('ascii')
        for asset in assets.values():
            body = body.replace('src="' + asset['file'] + '"', 'src="' + embedded(asset['file']) + '"')
        esc = html.escape
        controls = '<header style="padding:20px;background:#f1f6f5;margin-bottom:24px"><h2>公众号图文稿</h2><p>正文是可编辑文字，配图独立保留。此处只预览，尚未同步到公众号草稿箱。</p><p>同步会上传配图并保存草稿，最终群发由你在公众号确认。</p><p><a href="/wechat-settings?project=' + pid + '&amp;content=' + rid + '&amp;revision=' + str(revision) + '">确认这版图文并存入草稿箱 →</a></p><a href="?revision=' + str(revision) + '&amp;download=true">下载正文与独立配图</a></header>'
        if manifest['template_version']:
            label = '公众号已保存排版的本地副本' if manifest['imported_snapshot'] else '已套用公众号默认排版'
            controls = '<header style="padding:20px;background:#f1f6f5;margin-bottom:24px"><h2>' + label + '</h2><p>' + esc(manifest['template_name']) + ' · 模板 v' + str(manifest['template_version']) + '</p><p>文字、配图和排版已在系统留存；视频号卡片需在公众号另行处理。同步草稿后由你确认发布。</p><p><a href="/wechat-settings?project=' + pid + '&amp;content=' + rid + '&amp;revision=' + str(revision) + '">公众号排版与草稿设置</a> · <a href="?revision=' + str(revision) + '&amp;download=true">下载图文排版</a></p></header>'
        title = '<section style="border-bottom:1px solid #ddd;margin-bottom:24px"><small>文章标题</small><h1 style="font-size:24px">' + esc(display_title) + '</h1></section>'
        cover = ('<details><summary>封面图（单独设置，不重复插入正文）</summary><img style="width:100%" src="' + embedded(manifest['cover']) + '" alt="封面"></details>') if manifest['cover'] else ''
        headers['Content-Security-Policy'] = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        result = document(display_title, controls + title + cover + '<main>' + body + '</main>')
        require_current_export(g, request, pid, rid, content, assets, manifest['template_version'])
        return HTMLResponse(result, headers=headers)
