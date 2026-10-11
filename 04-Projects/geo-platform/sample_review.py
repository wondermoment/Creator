"""Authenticated client proof pages and portable, explicitly unapproved review packs."""
import hashlib
import html
import io
import json
import re
import zipfile
import base64
from PIL import Image
from fastapi import Request, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

CSS='''*{box-sizing:border-box}body{margin:0;background:#f3f5f7;color:#202a35;font:15px/1.85 "Microsoft YaHei",Arial,sans-serif}a{color:#1a73e8;text-decoration:none}header{background:white;border-bottom:1px solid #dbe1e6;padding:20px 4vw;display:flex;justify-content:space-between;align-items:center;gap:20px}header strong{font-size:20px}header small{color:#677582}main{max-width:1260px;margin:32px auto;display:grid;grid-template-columns:minmax(0,780px) 310px;gap:28px;padding:0 24px}article{background:#fff;border:1px solid #dce2e7;padding:48px 54px}h1{font-size:30px;line-height:1.5;margin:16px 0 24px}h2{font-size:21px;line-height:1.6;margin:36px 0 16px;border-left:4px solid #248e9c;padding-left:14px}p{margin:18px 0;text-align:justify;overflow-wrap:anywhere}.kicker{font-size:12px;letter-spacing:2px;color:#217d9c}.meta{font-size:12px;color:#71808e;border-bottom:1px solid #e2e7ec;padding-bottom:20px}.cover{background:#e9f4f4;padding:32px;margin:-48px -54px 32px;border-bottom:4px solid #239cac}.cover img{display:block;width:100%;max-height:380px;object-fit:contain}.cover small{display:block;margin-top:12px;color:#5e767d}figure{margin:30px 0;padding:12px;background:#f7f9fb;border:1px solid #e3e8ec}figure img{display:block;width:100%;height:auto}figcaption{font-size:12px;color:#677582;margin:10px 4px 0;line-height:1.6}aside section{background:#fff;border:1px solid #dce2e7;padding:20px;margin-bottom:16px}aside h3{margin:0 0 12px;font-size:16px}aside p,aside li{font-size:13px}aside ol,aside ul{padding-left:20px}.pill{padding:4px 9px;background:#fff4cf;color:#835c00;font-size:12px}.notice{background:#fff7de;border-left:3px solid #fbbc05;padding:12px;font-size:13px}.table-scroll{overflow-x:auto}table{border-collapse:collapse;font-size:13px;width:100%;margin:20px 0}td,th{border:1px solid #dbe1e7;padding:10px;text-align:left}tr:first-child{background:#edf5f7;font-weight:bold}details{font-size:13px;border-top:1px solid #e1e7eb;padding-top:12px;margin-top:12px}summary{cursor:pointer;color:#1a73e8}blockquote{margin:25px 0;padding:16px 20px;border-left:3px solid #4285f4;background:#f2f6fc}footer{font-size:12px;color:#677582;margin-top:34px;padding-top:20px;border-top:1px solid #e1e7eb}.navlist a{display:block;padding:9px 0;border-bottom:1px solid #eee;font-size:12px}.active{font-weight:bold;color:#202a35}.source-excerpt{white-space:pre-wrap;max-height:260px;overflow:auto}.actions{display:flex;gap:12px;flex-wrap:wrap}.actions a{padding:7px 12px;border:1px solid #dbe1e7;background:white;font-size:13px}@media(max-width:900px){main{grid-template-columns:1fr}article{padding:26px}.cover{margin:-26px -26px 24px}h1{font-size:25px}aside{order:-1}}@media print{header,.actions,.navlist{display:none}main{display:block;max-width:none;margin:0;padding:0}article{border:0;padding:20px}aside{page-break-before:always}figure{break-inside:avoid}body{background:white}.cover{margin:0}details{display:block}}'''

LAYOUT_STALE_MESSAGE = '图文排版已过期，请根据最新标题和正文重新制作配图后再送审'


def layout_current(content):
    layout = content.get('layout')
    if not layout:
        return True
    return (not layout.get('outdated')
            and layout.get('body_sha256') == hashlib.sha256(content['body'].encode()).hexdigest()
            and (not layout.get('title_sha256') or layout['title_sha256'] == hashlib.sha256(content['title'].encode()).hexdigest()))


def require_current_layout(content):
    if not layout_current(content):
        raise HTTPException(409, LAYOUT_STALE_MESSAGE)


def require_current_sources(g, c, pid, content):
    """A review may be unapproved, but its evidence must still match its snapshot."""
    g['require_content_provenance'](c, pid, content)
    message = '引用资料已更新或失效，请根据最新资料更新文章后再下载客户预览稿'
    if content.get('knowledge_outdated'):
        raise HTTPException(409, message)
    for snapshot in content.get('sources', []):
        if not isinstance(snapshot, dict) or not snapshot.get('id') or type(snapshot.get('version')) is not int:
            raise HTTPException(409, message)
        try:
            source = g['resource'](c, pid, snapshot['id'], 'knowledge')
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            raise HTTPException(409, message) from exc
        if (source['version'] != snapshot['version']
                or ('body' in snapshot and source['body'] != snapshot['body'])
                or not g['knowledge_usable'](c, pid, source, require_confirmed=False)):
            raise HTTPException(409, message)


def current_blocks(content):
    layout = content.get('layout', {})
    if layout_current(content) and layout.get('blocks'):
        return layout['blocks']
    return [{'text': p} for p in content['body'].split('\n\n') if p.strip()]


def render_article(project, content, claims, asset_url, siblings, href, client_links=None):
    esc=lambda x:html.escape(str(x),quote=True)
    layout=content.get('layout',{})
    matching=layout_current(content)
    blocks=current_blocks(content)
    if not matching: layout={}
    def figure(aid,caption): return '<figure><img loading="lazy" src="'+esc(asset_url(aid))+'" alt="'+esc(caption)+'"><figcaption>'+esc(caption)+'</figcaption></figure>'
    segments=[]
    for i,b in enumerate(blocks):
        t=b.get('text','').strip()
        if t and t!=content['title']:
            if b.get('type')=='table' and ' | ' in t:
                segments.append('<div class="table-scroll"><table>'+''.join('<tr>'+''.join('<td>'+esc(cell)+'</td>' for cell in row.split(' | '))+'</tr>' for row in t.splitlines())+'</table></div>')
            elif re.match(r'^(?:[一二三四五六七八九十]+|[0-9]+)[、．.]',t) and len(t)<140:
                segments.append('<h2>'+esc(t)+'</h2>')
            elif len(t)<160 and (t.startswith(('“','"')) and t.endswith(('”','"'))): segments.append('<blockquote>'+esc(t)+'</blockquote>')
            else: segments.append('<p>'+esc(t).replace('\n','<br>')+'</p>')
        for aid in b.get('image_ids',[]): segments.append(figure(aid,'原稿配图 · '+b.get('location','')+'；图示内容请客户复核'))
        for f in layout.get('figures',[]):
            if f['after']==i: segments.append(figure(f['asset_id'],f['caption']))
    cover = ('<div class="cover"><img src="'+esc(asset_url(layout['cover_id']))+'" alt="企业封面候选"><small>封面候选 · 渠道裁切与使用范围待客户确认</small></div>') if layout.get('cover_id') else '<div class="notice">正文与表格已整理；封面及配图待选。</div>'
    if layout.get('wechat_html'):
        import wechat_layout
        segments = [wechat_layout.resolve_fragment(layout['wechat_html'], lambda aid, index, caption: asset_url(aid))]
        # The saved WeChat layout already contains its own brand header and article images.
        cover = ''
    relevant=[x for x in claims if x.get('knowledge_id')==content.get('original_knowledge_id')]
    check=''.join('<details><summary>'+esc(x['title'])+' · '+str(len(x['excerpts']))+' 处需核准</summary><p>'+esc(x['requirement'])+'</p>'+''.join('<div class="source-excerpt"><b>'+esc(e['location'])+'</b><br>'+esc(e['text'])+'</div>' for e in x['excerpts'])+'</details>' for x in relevant)
    status='当前版本已审核' if content['status']=='approved' and content.get('approved_revision')==content['revision'] else '客户预览 · 尚未批准发送'
    approval = content.get('approval_summary')
    if approval is not None and not approval['effective_approved']:
        status = '依据待核验 · 尚未批准发送' if approval['sources_outdated'] else '客户预览 · 尚未批准发送'
    document = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+esc(content['title'])+' · 客户预览</title><style>'+CSS+'</style><header><div><strong>'+esc(project['name'])+'</strong><br><small>品牌铸匠 GEO · 图文内容交付预览</small></div><div><span class="pill">'+status+'</span><br><small>版本 '+str(content['revision'])+' · 原稿排版与素材审阅</small></div></header><main><article>'+cover+'<span class="kicker">制造业 · 涂装前处理</span><h1>'+esc(content['title'])+'</h1><div class="meta">和拓化学 · 企业技术内容 / 排版稿 v'+str(content['revision'])+' / '+str(len(content['body']))+' 字符</div>'+''.join(segments)+'<footer>原稿与配图：客户提供资料。以上为内容审阅版，技术参数以客户核准的适用条件和有效资料为准。审核意见仅在侧栏展示，不自动追加到拟发布正文。</footer></article><aside><section><h3>客户审阅提示</h3><div class="notice">'+status+'。当前预览不代表已经向平台发送。</div><p>建议渠道：'+esc(' / '.join(content['channels']) or '待选择')+'<br>发布时间：待客户确认<br>发布账号：待绑定 / 确认</p><ul>'+''.join('<li>'+esc(n)+'</li>' for n in content.get('review_notes',[]))+'</ul>'+('' if matching else '<p class="notice">标题或正文已修改，旧配图已暂停展示；请重新制作图文排版后再送审。</p>')+'<div class="actions"><a href="'+esc(href('review'))+'">返回工作台审核</a></div></section><section><h3>事实与表述核验</h3><p>下列为规则筛查发现的审阅点，不是认定原文错误；须结合原始检测、测算及客户意见核准。</p>'+check+'</section><section class="navlist"><h3>本批 '+str(len(siblings))+' 篇预览</h3>'+''.join('<a class="'+('active' if x['id']==content['id'] else '')+'" href="'+esc(href(x['id']))+'">'+esc(x['title'])+'</a>' for x in siblings)+'</section></aside></main></html>'


    if client_links:
        wechat_url = client_links['reader'].replace('/client-preview?', '/wechat-preview?')
        document = document.replace('<article>', '<article><section class="actions" style="margin-bottom:24px"><a target="_blank" rel="noopener" href="'+esc(wechat_url)+'">公众号图文稿 · 文字与独立配图</a></section>', 1)
        controls = '<section class="client-preview-actions" style="border-top:1px solid #dce2e7;margin-top:28px;padding-top:24px"><h2>发送客户前，先看完整效果</h2><p>按手机阅读宽度检查正文与配图；下载稿已包含全部图片，可作为文件发送给客户。</p><div class="actions"><a target="_blank" rel="noopener" href="'+esc(client_links['reader'])+'">手机阅读预览</a><a href="'+esc(client_links['download'])+'">下载客户预览稿（HTML）</a><a href="'+esc(client_links['download'].replace('&download=true','&format=png'))+'">下载预览长图（PNG）</a></div><p class="hint">当前是本机预览，客户无法打开本机地址。可将 PNG 长图直接发微信。HTML 文件需用浏览器打开。客户意见回传后，再由项目成员在系统审核。</p></section>'
        document = document.replace('</article>', controls+'</article>', 1)
    return document


READER_CSS = CSS + '''
body{background:#eef1f3;font-family:"Microsoft YaHei",Arial,sans-serif}
.reader-shell{max-width:430px;margin:28px auto;background:white;box-shadow:0 4px 24px #142b3510}
.reader-top{padding:12px 20px;border-bottom:1px solid #eee;color:#68787e;font-size:12px}
article{border:0;padding:24px 20px;font-size:16px;line-height:1.9}
h1{font-size:24px;line-height:1.55;margin-top:12px}h2{font-size:19px;margin:28px 0 16px}
p{text-align:left;margin:20px 0}figure{margin:26px -8px;padding:0;background:white;border:0}figcaption{font-size:11px;color:#8a969b}
.cover{padding:0;margin:0 0 22px;background:white;border:0}.cover img{max-height:none}.cover small{display:none}
.meta{font-size:12px;line-height:1.8;color:#78858a}.kicker{display:none}
.reader-confirm{margin-top:36px;padding:22px 18px;background:#f3f8f6;border-top:3px solid #159b86;font-size:13px}
.reader-confirm h2{margin:0 0 12px;border:0;padding:0}.reader-confirm p{font-size:13px}
.reader-tools{max-width:430px;margin:12px auto 28px;font-size:13px;padding:0 12px}.reader-tools a{display:inline-block;padding:10px;border:1px solid #cad7d9;background:white}
@media(max-width:480px){body{background:white}.reader-shell{margin:0 auto;box-shadow:none}article{padding:22px 18px}}
@media print{.reader-tools,.reader-top{display:none}.reader-shell{max-width:none;box-shadow:none;margin:0}article{padding:0}.reader-confirm{break-inside:avoid}}
'''


def render_reader(project, content, asset_url, download_url=None):
    """Public-facing copy only: no other articles, prompts, internal notes or credentials."""
    require_current_layout(content)
    source = render_article(project, content, [], asset_url, [], lambda _: '')
    article = re.search(r'<article>(.*?)</article>', source, re.S).group(1)
    article = re.sub(r'<footer>.*?</footer>', '', article, flags=re.S)
    article = article.replace('loading="lazy"', 'loading="eager"')
    # Keep article content as rendered, but label this snapshot independently of approval.
    esc=lambda value:html.escape(str(value),quote=True)
    checksum=hashlib.sha256(content['body'].encode()).hexdigest()[:12]
    confirmation='<section class="reader-confirm"><h2>请确认这版图文</h2><p>请核对正文、配图、技术参数与适用条件，并回复具体修改位置。</p><p>文章版本 v'+str(content['revision'])+' · 正文校验 '+checksum+'</p><p>本稿仅供审阅，尚未发送到发布平台。客户回复后，仍需项目成员在系统完成审核。</p></section>'
    tools=('<div class="reader-tools"><a href="'+esc(download_url.replace('&download=true','&format=png'))+'">下载客户预览长图</a> <a href="'+esc(download_url)+'">下载这版客户预览稿（HTML）</a><p>长图可直接发微信给客户确认。本机地址不可外部访问；HTML 文件已内嵌图片，需用浏览器打开。</p></div>') if download_url else ''
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; img-src data:; style-src &apos;unsafe-inline&apos;; base-uri &apos;none&apos;; form-action &apos;none&apos;"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+esc(content['title'])+' · 客户阅读预览</title><style>'+READER_CSS+'</style><div class="reader-shell"><div class="reader-top">'+esc(project['name'])+' · 图文确认稿 v'+str(content['revision'])+'</div><article>'+article+confirmation+'</article></div>'+tools+'</html>'


def preview_asset_bytes(g, c, pid, aid):
    a=g['resource'](c,pid,aid,'asset')
    folder=(g['DB_PATH'].parent/'assets'/pid).resolve()
    path=(folder/a['storage_key']).resolve()
    if not path.is_relative_to(folder):
        raise HTTPException(409,'预览图片路径无效，请先修复图片')
    try:
        with path.open('rb') as stream:
            raw=stream.read(15*1024*1024+1)
    except OSError as exc:
        raise HTTPException(409,'预览图片缺失或无法读取，请先修复图片再下载') from exc
    if len(raw)>15*1024*1024:
        raise HTTPException(409,'预览图片过大，请压缩后重试')
    digest=hashlib.sha256(raw).hexdigest()
    if a.get('sha256') and a['sha256']!=digest:
        raise HTTPException(409,'预览图片与素材记录不一致，请重新上传图片')
    return raw, {'storage_key':a['storage_key'],'sha256':digest}


def require_unchanged_preview_assets(g, c, pid, snapshots):
    for aid, snapshot in snapshots.items():
        try:
            _, current=preview_asset_bytes(g,c,pid,aid)
        except HTTPException as exc:
            if exc.status_code not in (404,409):raise
            raise HTTPException(409,'生成期间配图已变更或不可用，请重新打开文章下载') from exc
        if current!=snapshot:
            raise HTTPException(409,'生成期间配图已变更，请重新打开文章下载')


def preview_image_format(raw):
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt=im.format;im.verify()
        mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp','GIF':'image/gif'}.get(fmt)
        if not mime:raise ValueError('Unsupported image format')
        return mime, {'PNG':'png','JPEG':'jpg','WEBP':'webp','GIF':'gif'}[fmt]
    except Exception as exc:
        raise HTTPException(409,'预览图片损坏或格式不支持，请先修复图片') from exc


def embedded_asset_url(g, c, pid, snapshots=None):
    """Tenant-scoped raster images, embedded for offline sharing; fail closed."""
    cache={};total=0
    def resolve(aid):
        nonlocal total
        if aid in cache:return cache[aid]
        if len(cache)>=40:
            raise HTTPException(409,'预览图片过大，请压缩后重试')
        raw,snapshot=preview_asset_bytes(g,c,pid,aid)
        total+=len(raw)
        if total>40*1024*1024:raise HTTPException(409,'预览稿图片总量过大，请压缩后重试')
        mime,_=preview_image_format(raw)
        cache[aid]='data:'+mime+';base64,'+base64.b64encode(raw).decode('ascii')
        if snapshots is not None:snapshots[aid]=snapshot
        return cache[aid]
    return resolve


def register(g):
    import wechat_export
    wechat_export.register(g)
    app=g['app']; db=g['db']; scope=g['scope']; items=g['items']; resource=g['resource']
    @app.get('/api/projects/{pid}/writing-reference')
    def writing_reference(pid:str,request:Request):
        with db() as c:
            g['require_prompt_admin'](c,request,pid)
            records=items(c,pid,'writing_reference')
            if not records: raise HTTPException(404,'当前企业没有配置写作方法参考')
            return records[0]
    @app.get('/api/projects/{pid}/contents/{rid}/proof')
    def proof(pid:str,rid:str,request:Request,revision:int | None=Query(default=None,ge=1)):
        with db() as c:
            scope(c,request,pid); content=resource(c,pid,rid,'content')
            if revision is not None and content['revision'] != revision:
                raise HTTPException(409,'内容版本已更新，请关闭预览并刷新后重新审阅')
            if not content.get('layout'): raise HTTPException(404,'此内容尚无图文排版稿')
            content['approval_summary'] = g['content_approval_summary'](c, pid, content)
            siblings=sorted([x for x in items(c,pid,'content') if x.get('layout') and x.get('import_batch')==content.get('import_batch')],key=lambda x:int(re.match(r'\d+',x['title']).group()) if re.match(r'\d+',x['title']) else 999)
            versions={x['id']:x['revision'] for x in siblings}
            return HTMLResponse(render_article(g['project'](c,pid),content,items(c,pid,'evidence_claim'),lambda aid:f'/api/projects/{pid}/assets/{aid}/file',siblings,lambda rid:'/#content' if rid=='review' else f'/api/projects/{pid}/contents/{rid}/proof?revision={versions[rid]}',client_links={'reader':f'/api/projects/{pid}/contents/{content["id"]}/client-preview?revision={content["revision"]}','download':f'/api/projects/{pid}/contents/{content["id"]}/client-preview?revision={content["revision"]}&download=true'}),headers={'Cache-Control':'no-store','X-Content-Revision':str(content['revision']),'X-Layout-Status':'current' if layout_current(content) else 'stale'})

    @app.get('/api/projects/{pid}/contents/{rid}/client-preview')
    def client_preview(pid:str,rid:str,request:Request,revision:int=Query(ge=1),download:bool=False,format:str=Query(default="html",pattern="^(html|png)$")):
        with db() as c:
            scope(c,request,pid)
            content=resource(c,pid,rid,'content')
            if content['revision']!=revision:
                raise HTTPException(409,'内容版本已更新，请返回文章重新打开预览')
            if not content.get('layout'):raise HTTPException(404,'此内容尚无图文排版稿')
            require_current_layout(content)
            require_current_sources(g, c, pid, content)
            # Both modes embed the same verified images; downloaded HTML needs no login.
            asset_snapshots={}
            layout_snapshot=json.dumps(content['layout'],sort_keys=True,ensure_ascii=False)
            document=render_reader(g['project'](c,pid),content,embedded_asset_url(g,c,pid,asset_snapshots),
                None if download or format!='html' else f'/api/projects/{pid}/contents/{rid}/client-preview?revision={revision}&download=true')
        if format != 'html':
            from preview_images import render_images
            data=render_images(document)
            with db() as c:
                scope(c,request,pid)
                current=resource(c,pid,rid,'content')
                if current['revision']!=revision:raise HTTPException(409,'内容版本已更新，请重新下载')
                require_current_layout(current)
                require_current_sources(g, c, pid, current)
                if json.dumps(current.get('layout'),sort_keys=True,ensure_ascii=False)!=layout_snapshot:
                    raise HTTPException(409,'生成期间图文排版已变更，请重新打开文章下载')
                require_unchanged_preview_assets(g,c,pid,asset_snapshots)
            extension='png'
            return Response(data,media_type='image/png',headers={
                'Cache-Control':'no-store','X-Content-Revision':str(revision),
                'Content-Disposition':f'attachment; filename="customer-preview-{rid}-v{revision}.{extension}"'})
        headers={'Cache-Control':'no-store','X-Content-Revision':str(revision),
                     'Content-Security-Policy':"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"}
        if download:headers['Content-Disposition']=f'attachment; filename="customer-preview-{rid}-v{revision}.html"'
        return HTMLResponse(document,headers=headers)

    @app.get('/api/projects/{pid}/review-pack')
    def pack(pid:str,request:Request,batch:str=''):
        with db() as c:
            scope(c,request,pid,['owner','editor','reviewer'])
            rows=sorted([x for x in items(c,pid,'content') if x.get('layout') and (not batch or x.get('import_batch')==batch)],key=lambda x:(x.get('import_batch',''),int(re.match(r'\d+',x['title']).group()) if re.match(r'\d+',x['title']) else 999))
            if not rows: raise HTTPException(404,'暂无图文审阅稿')
            for row in rows:
                require_current_layout(row)
                require_current_sources(g, c, pid, row)
            mapping={x['id']:f'article-{i+1:02d}.html' for i,x in enumerate(rows)}
            assets={}; snapshots={}; total=0
            def url(aid):
                nonlocal total
                if aid not in assets:
                    if len(assets)>=512:raise HTTPException(409,'审阅包图片过多，请按批次下载')
                    try:
                        raw,snapshot=preview_asset_bytes(g,c,pid,aid)
                    except HTTPException as exc:
                        if exc.status_code==404:
                            raise HTTPException(409,'审阅包引用图片不存在或不属于当前企业，请修复配图') from exc
                        raise
                    _,extension=preview_image_format(raw)
                    total+=len(raw)
                    if total>256*1024*1024:raise HTTPException(409,'审阅包图片总量过大，请按批次下载')
                    # Archive paths come from a digest and decoded format, never stored filenames.
                    name='images/'+hashlib.sha256(aid.encode()).hexdigest()+'.'+extension
                    assets[aid]=(name,raw);snapshots[aid]=snapshot
                return assets[aid][0]
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
                for row in rows:
                    z.writestr(mapping[row['id']],render_article(g['project'](c,pid),row,items(c,pid,'evidence_claim'),url,rows,lambda rid:'index.html' if rid=='review' else mapping[rid]))
                for name,raw in assets.values():
                    z.writestr(name,raw)
                project_name=g['project'](c,pid)['name']
                z.writestr('index.html','<!doctype html><meta charset="utf-8"><title>'+html.escape(project_name)+'图文审阅包</title><style>'+CSS+'</style><main style="display:block"><h1>'+html.escape(project_name)+' · 图文内容客户审阅包</h1><p class="notice">本包为审阅材料，不是发布授权或已发布回执。客户确认事实、图片与最终渠道版本后，再在系统完成审核。解压后打开本页。</p>'+''.join('<p><a href="'+mapping[x['id']]+'">'+html.escape(x['title'])+'</a></p>' for x in rows)+'</main>')
                z.writestr('manifest.json',json.dumps({'type':'customer_review_pack','published':False,'project':project_name,'assets':[{'id':aid,'file':assets[aid][0],'sha256':snapshot['sha256']} for aid,snapshot in snapshots.items()],'articles':[{'id':x['id'],'title':x['title'],'revision':x['revision'],'status':x['status'],'body_sha256':hashlib.sha256(x['body'].encode()).hexdigest()} for x in rows]},ensure_ascii=False,indent=2))
            require_unchanged_preview_assets(g,c,pid,snapshots)
            return Response(stream.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="customer-review.zip"'})
