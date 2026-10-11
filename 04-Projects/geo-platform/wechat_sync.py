"""Official WeChat draft-only connector. Secrets never appear in response DTOs."""
import hashlib
import html
import io
import ipaddress
import json
import re
import threading
import time
from urllib.parse import parse_qsl, urlsplit
from contextlib import contextmanager
from html.parser import HTMLParser

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, SecretStr

import wechat_export


def upload_image(asset, name=None):
    """WeChat uploadimg rejects WebP even when its CDN returns that format."""
    from PIL import Image
    raw, mime = asset['raw'], asset['mime']
    filename = name or asset['file'].split('/')[-1]
    if mime == 'image/webp':
        with Image.open(io.BytesIO(raw)) as image:
            if getattr(image, 'n_frames', 1) != 1:
                raise WechatError('动态图需先转为微信支持的 GIF 格式')
            buffer = io.BytesIO()
            image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(buffer, format='PNG')
        raw, mime = buffer.getvalue(), 'image/png'
        filename = filename.rsplit('.', 1)[0] + '.png'
    return filename, raw, mime

API = 'https://api.weixin.qq.com'
_locks = {}
_guard = threading.Lock()


def article_digest(content):
    """Send plain text explicitly; WeChat's HTML fallback can expose entities."""
    title = ' '.join(str(content.get('title', '')).split())
    for block in wechat_export.review.current_blocks(content):
        text = ' '.join(str(block.get('text', '')).split())
        if text and text != title:
            return html.unescape(text)[:120]
    return ''


def valid_image_url(url):
    # Both origins have been returned by the official uploadimg endpoint.
    try:
        parsed = urlsplit(url)
        return (parsed.scheme in ('http', 'https') and parsed.hostname in ('mmbiz.qpic.cn', 'mmecoa.qpic.cn')
                and not parsed.username and not parsed.password and parsed.port is None and not parsed.fragment)
    except (ValueError, TypeError):
        return False


def article_signature(article):
    class BodyCheck(HTMLParser):
        def __init__(self): super().__init__(); self.text = []; self.images = []; self.links = []
        def handle_data(self, value): self.text.append(value)
        def handle_starttag(self, tag, attrs):
            if tag == 'a' and dict(attrs).get('href'):
                self.links.append(dict(attrs)['href'])
            if tag == 'img':
                attributes = dict(attrs)
                self.images.append(attributes.get('data-src') or attributes.get('src', ''))
    parsed = BodyCheck()
    parsed.feed(article.get('content', ''))
    return {'title': article.get('title', ''), 'thumb_media_id': article.get('thumb_media_id', ''),
            'digest': article.get('digest', ''),
            'text_sha256': hashlib.sha256(' '.join(''.join(parsed.text).split()).encode()).hexdigest(),
            'images': parsed.images, 'links': parsed.links}


def draft_matches(remote, expected):
    articles = remote.get('news_item', [])
    if len(articles) != 1: return False
    actual = article_signature(articles[0])
    def identity(url):
        if not valid_image_url(url): return ('invalid', url)
        p = urlsplit(url)
        # WeChat rewrites HTTP /0 originals to HTTPS /640 display variants.
        return p.hostname, re.sub(r'/(0|640)$', '', p.path), p.query
    return (all(actual.get(k) == expected.get(k) for k in ('title', 'thumb_media_id', 'text_sha256'))
            and ('links' not in expected or actual['links'] == expected['links'])
            and ('digest' not in expected or actual['digest'] == expected['digest'])
            and len(actual['images']) == len(expected.get('images', []))
            and all(valid_image_url(url) for url in actual['images'])
            and [identity(url) for url in actual['images']] == [identity(url) for url in expected.get('images', [])])


class WechatError(Exception):
    def __init__(self, message, code=None, ip=''):
        super().__init__(message)
        self.code, self.ip = code, ip


def call(path, token='', data=None, files=None):
    # Fixed official origin; do not forward credentials via redirects or environment proxies.
    try:
        endpoint, _, query = path.partition('?')
        params = dict(parse_qsl(query))
        if token: params['access_token'] = token
        with httpx.Client(timeout=45, follow_redirects=False, trust_env=False) as client:
            response = client.post(API + endpoint, params=params,
                                   json=data if files is None else None, files=files)
        if response.status_code != 200:
            raise WechatError('微信接口暂不可用，请稍后检查连接')
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError()
    except (httpx.HTTPError, ValueError):
        raise WechatError('微信接口连接中断或回执无效') from None
    code = result.get('errcode', 0)
    if code:
        ip = ''
        if code == 40164:
            match = re.search(r'invalid ip\s+([0-9a-fA-F:.]+)', str(result.get('errmsg', '')))
            if match:
                try: ip = str(ipaddress.ip_address(match[1].rstrip('.')))
                except ValueError: pass
        message = {40164: '微信拒绝当前出口 IP，请将该地址加入 API IP 白名单',
                   40125: 'AppSecret 无效，请核对或更新后台密钥',
                   40013: 'AppID 无效，请核对公众号',
                   48001: '此账号没有当前接口权限，请核对微信认证与接口权限',
                   40001: '接口凭证失效，请重新测试连接',
                   42001: '接口凭证过期，请重新测试连接',
                   45009: '微信接口调用达到频率限制，请稍后重试'}.get(code, '微信接口拒绝本次请求')
        raise WechatError(message + '（错误码 ' + str(code) + '）', code, ip)
    return result


def cipher(g):
    path = g['DB_PATH'].parent / 'connector.key'
    with _guard:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream: stream.write(Fernet.generate_key())
        return Fernet(path.read_bytes())


def config(c, g, pid):
    return next(iter(g['items'](c, pid, 'wechat_config')), None)


def public_config(item):
    item = item or {}
    return {key: item.get(key, default) for key, default in
            [('appid', ''), ('name', ''), ('version', 0), ('status', 'not_configured'),
             ('verified_at', ''), ('error', ''), ('required_ip', '')]} | {'has_secret': bool(item.get('encrypted_secret'))}


def save_config(g, c, pid, appid, secret, name='和拓实业HEROTO'):
    old = config(c, g, pid) or {}
    if not secret and (old.get('appid') != appid or not old.get('encrypted_secret')):
        raise HTTPException(400, '首次绑定或更换 AppID 时必须填写密钥')
    item = dict(appid=appid, name=name, version=old.get('version', 0) + 1,
                encrypted_secret=cipher(g).encrypt(secret.encode()).decode() if secret else old['encrypted_secret'],
                status='configured', verified_at='', error='', required_ip='', token_expires=0)
    g['put'](c, pid, 'wechat_config', item, old.get('id'))
    return public_config(item)


@contextmanager
def locked(g, pid):
    with _guard:
        lock = _locks.setdefault((str(g['DB_PATH']), pid), threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, '公众号任务正在进行，请等待回执')
    try: yield
    finally: lock.release()


def access_token(g, pid, cfg, force=False):
    if not force and cfg.get('token_expires', 0) > time.time() + 120 and cfg.get('encrypted_token'):
        return cipher(g).decrypt(cfg['encrypted_token'].encode()).decode()
    secret = cipher(g).decrypt(cfg['encrypted_secret'].encode()).decode()
    result = call('/cgi-bin/stable_token', data={'grant_type': 'client_credential', 'appid': cfg['appid'],
                                              'secret': secret, 'force_refresh': False})
    token = result.get('access_token')
    if not isinstance(token, str) or not token or type(result.get('expires_in')) is not int:
        raise WechatError('微信未返回有效接口凭证')
    with g['db']() as c:
        current = config(c, g, pid)
        if not current or current['version'] != cfg['version']:
            raise HTTPException(409, '绑定已变化，请重新操作')
        current.update(encrypted_token=cipher(g).encrypt(token.encode()).decode(),
                       token_expires=time.time() + result['expires_in'])
        g['put'](c, pid, 'wechat_config', current, current['id'])
    return token


def test_connection(g, pid, cfg):
    try:
        token = access_token(g, pid, cfg, force=True)
        # This request is read-only. It proves draft-read access, not draft-write acceptance.
        result = call('/cgi-bin/draft/batchget', token, {'offset': 0, 'count': 1, 'no_content': 1})
        if type(result.get('total_count')) is not int:
            raise WechatError('微信未返回草稿列表回执')
        update = dict(status='verified_read', verified_at=g['now'](), error='', required_ip='')
    except WechatError as exc:
        update = dict(status='blocked', verified_at='', error=str(exc), required_ip=exc.ip,
                      token_expires=0)
    with g['db']() as c:
        current = config(c, g, pid)
        if not current or current['version'] != cfg['version']:
            raise HTTPException(409, '绑定已变化，请重新测试')
        current.update(update)
        g['put'](c, pid, 'wechat_config', current, current['id'])
    return public_config(current)


class Binding(BaseModel):
    appid: str = Field(pattern=r'^wx[0-9a-fA-F]{16}$')
    secret: SecretStr = SecretStr('')
    name: str = Field(default='', max_length=120)
    version: int = Field(ge=0)


class DraftRequest(BaseModel):
    revision: int = Field(ge=1)
    confirm: bool = False
    binding_version: int = Field(default=0, ge=0)
    appid: str = Field(default='', max_length=32)
    template_version: int = Field(default=0, ge=0)


def register(g):
    app = g['app']

    @app.get('/wechat-settings')
    def settings_page():
        return FileResponse(g['ROOT'] / 'static' / 'wechat-settings.html')

    @app.get('/api/projects/{pid}/wechat')
    def get_settings(pid: str, request: Request):
        with g['db']() as c:
            g['scope'](c, request, pid, ['owner'])
            return public_config(config(c, g, pid))

    @app.put('/api/projects/{pid}/wechat')
    def bind(pid: str, request: Request, body: Binding):
        with locked(g, pid), g['db']() as c:
            user, _ = g['scope'](c, request, pid, ['owner'])
            old = config(c, g, pid) or {}
            if old.get('version', 0) != body.version:
                raise HTTPException(409, '绑定配置已更新，请刷新')
            secret = body.secret.get_secret_value().strip()
            if len(secret) > 256: raise HTTPException(400, '密钥长度无效')
            result = save_config(g, c, pid, body.appid, secret, body.name)
            g['event'](c, pid, user['user_id'], '保存公众号绑定', '凭证加密保存，等待接口测试')
            return result

    @app.post('/api/projects/{pid}/wechat/test')
    def test(pid: str, request: Request):
        with locked(g, pid):
            with g['db']() as c:
                g['scope'](c, request, pid, ['owner'])
                cfg = config(c, g, pid)
                if not cfg: raise HTTPException(409, '请先保存公众号配置')
            return test_connection(g, pid, cfg)

    @app.get('/api/projects/{pid}/contents/{rid}/wechat-draft')
    def draft_status(pid: str, rid: str, request: Request):
        import wechat_layout
        with g['db']() as c:
            g['scope'](c, request, pid)
            content = g['resource'](c, pid, rid, 'content')
            cfg = config(c, g, pid) or {}
            template = wechat_layout.selected(g, c, pid)
            return {'next_digest': template.get('digest', '') if wechat_layout.is_source(template, content) else article_digest(content), 'revision': content['revision'],
                    'template': wechat_layout.status(template), 'imported_snapshot': wechat_layout.is_source(template, content),
                    'binding': {k: cfg.get(k, 0 if k == 'version' else '') for k in ('appid', 'name', 'version')},
                    'records': [x for x in g['items'](c, pid, 'wechat_draft') if x['content_id'] == rid]}

    @app.post('/api/projects/{pid}/contents/{rid}/wechat-draft')
    def create_draft(pid: str, rid: str, request: Request, body: DraftRequest):
        if not body.confirm: raise HTTPException(400, '请确认把这版图文存入公众号草稿箱')
        with locked(g, pid):
            with g['db']() as c:
                actor, _ = g['scope'](c, request, pid, ['owner', 'editor'])
                cfg = config(c, g, pid)
                if not cfg or cfg['status'] != 'verified_read':
                    raise HTTPException(409, '请在后台保存公众号配置并通过连接测试')
                if body.appid != cfg['appid'] or body.binding_version != cfg['version']:
                    raise HTTPException(409, '公众号绑定已变化或缺少确认信息，请刷新并确认目标公众号后重试')
                content = g['resource'](c, pid, rid, 'content')
                if content['revision'] != body.revision: raise HTTPException(409, '文章版本已变化')
                html_body, assets, manifest = wechat_export.prepare(g, c, pid, content)
                if manifest['imported_snapshot']:
                    raise HTTPException(409, '此篇已回同步公众号最新排版，请在原草稿继续编辑，不重复创建')
                if body.template_version != manifest['template_version']:
                    raise HTTPException(409, '排版模板已变化，请重新预览并确认')
                if not manifest['cover']: raise HTTPException(409, '请先配置独立封面')
                fingerprint = hashlib.sha256(json.dumps([cfg['appid'], rid, body.revision, html_body, manifest],
                                                       sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                records = g['items'](c, pid, 'wechat_draft')
                unresolved = next((x for x in records if x['content_id'] == rid and x['appid'] == cfg['appid']
                                   and x['status'] in ('preparing', 'sending', 'created', 'needs_review')), None)
                if unresolved:
                    raise HTTPException(409, '此文章有未核对的同步任务，请先核对公众号草稿箱；修改版本也不会自动重发')
                existing = next((x for x in records if x['fingerprint'] == fingerprint), None)
                if existing and existing['status'] != 'failed': return existing
                # A template/renderer change must not silently create a second
                # remote draft for an already delivered article revision.
                delivered = next((x for x in records if x['content_id'] == rid and x['appid'] == cfg['appid']
                                  and x['revision'] == body.revision and x['status'] == 'synced'), None)
                if delivered:
                    raise HTTPException(409, '此版本已同步到公众号草稿箱，当前排版与已同步版本不同；请先核对原草稿，不重复创建')
                job = {'content_id': rid, 'revision': body.revision, 'fingerprint': fingerprint,
                       'appid': cfg['appid'], 'status': 'preparing', 'media_id': '', 'error': '',
                       'actor': actor['user_id'], 'published': False}
                jid = g['put'](c, pid, 'wechat_draft', job, existing['id'] if existing else None)
            # A crash after "sending" is deliberately not retried automatically.
            def save(**changes):
                job.update(changes)
                with g['db']() as c: g['put'](c, pid, 'wechat_draft', job, jid)

            def check():
                wechat_export.require_current_export(g, request, pid, rid, content, assets, manifest['template_version'])
                with g['db']() as c:
                    g['scope'](c, request, pid, ['owner', 'editor'])
                    current = config(c, g, pid)
                    if not current or current['version'] != cfg['version']:
                        raise HTTPException(409, '公众号绑定已变化')

            try:
                token = access_token(g, pid, cfg)
                mapped = {}
                # Only upload body images as inline image assets.
                for path in dict.fromkeys(x['file'] for x in manifest['images'] if x['role'] == 'body'):
                    check()
                    asset = next(a for a in assets.values() if a['file'] == path)
                    result = call('/cgi-bin/media/uploadimg', token,
                                  files={'media': upload_image(asset)})
                    url = result.get('url', '')
                    if not valid_image_url(url): raise WechatError('微信未返回有效配图地址')
                    mapped[path] = url
                check()
                cover = next(a for a in assets.values() if a['file'] == manifest['cover'])
                # type belongs in the URL query alongside the access_token.
                result = call('/cgi-bin/material/add_material?type=image', token,
                              files={'media': upload_image(cover, 'cover.' + cover['file'].split('.')[-1])})
                thumb = result.get('media_id')
                if not isinstance(thumb, str) or not thumb: raise WechatError('微信未返回封面素材编号')
                import html
                for path, url in mapped.items():
                    html_body = html_body.replace('src="' + path + '"', 'src="' + html.escape(url, quote=True) + '"')
                html_body = wechat_export.wechat_layout.image_link_markup(html_body)
                check()
                article = {'title': content['title'], 'content': html_body, 'thumb_media_id': thumb,
                           'digest': article_digest(content),
                           'need_open_comment': 0, 'only_fans_can_comment': 0}
                with g['db']() as c:
                    template = wechat_export.wechat_layout.selected(g, c, pid)
                    if template: article['author'] = template.get('author', '')
                save(status='sending', expected=article_signature(article))
                result = call('/cgi-bin/draft/add', token, {'articles': [article]})
                media_id = result.get('media_id')
                if not isinstance(media_id, str) or not media_id: raise WechatError('微信草稿回执缺少编号')
                save(status='created', media_id=media_id)
                remote = call('/cgi-bin/draft/get', token, {'media_id': media_id})
                if not draft_matches(remote, job['expected']):
                    raise WechatError('草稿已创建，但回读内容未通过核对')
                check()
                save(status='synced', error='', synced_at=g['now']())
            except (WechatError, HTTPException) as exc:
                message = str(exc) if isinstance(exc, WechatError) else str(exc.detail)
                save(status='needs_review' if job['status'] in ('sending', 'created') else 'failed', error=message)
            except Exception:
                save(status='needs_review' if job['status'] in ('sending', 'created') else 'failed',
                     error='同步中断，请核对公众号草稿箱后处理')
            return {'id': jid, **job}

    @app.post('/api/projects/{pid}/contents/{rid}/wechat-draft/{jid}/reconcile')
    def reconcile(pid: str, rid: str, jid: str, request: Request):
        """Read remote evidence only; never create a replacement on uncertain outcomes."""
        with locked(g, pid):
            with g['db']() as c:
                actor, _ = g['scope'](c, request, pid, ['owner', 'editor'])
                job = g['resource'](c, pid, jid, 'wechat_draft')
                if job['content_id'] != rid: raise HTTPException(404, '同步记录不属于此文章')
                cfg = config(c, g, pid)
                if not cfg or cfg['appid'] != job['appid']: raise HTTPException(409, '请切回任务原公众号后核对')
                if job['status'] == 'preparing' and not job.get('expected'):
                    job.update(status='failed', error='上次在提交草稿前中断，可重新确认同步')
                    g['put'](c, pid, 'wechat_draft', job, jid)
                    return job
                if not job.get('expected'): raise HTTPException(409, '旧任务缺少回读快照，需人工核对，不自动重发')
            try:
                token = access_token(g, pid, cfg)
                media_id = job.get('media_id', '')
                if not media_id:
                    matches = []
                    for offset in range(0, 100, 20):
                        batch = call('/cgi-bin/draft/batchget', token, {'offset': offset, 'count': 20, 'no_content': 0})
                        for item in batch.get('item', []):
                            if draft_matches(item.get('content', {}), job['expected']) and item.get('media_id'):
                                matches.append(item['media_id'])
                        if offset + 20 >= batch.get('total_count', 0): break
                    matches = list(dict.fromkeys(matches))
                    if len(matches) != 1:
                        raise WechatError('最近100篇草稿中未找到唯一匹配，保留待核对状态；不会自动重发')
                    media_id = matches[0]
                remote = call('/cgi-bin/draft/get', token, {'media_id': media_id})
                if not draft_matches(remote, job['expected']): raise WechatError('远端内容与提交快照不一致，请在公众号核对')
                with g['db']() as c:
                    g['scope'](c, request, pid, ['owner', 'editor'])
                    current_cfg = config(c, g, pid)
                    if not current_cfg or current_cfg['version'] != cfg['version']: raise HTTPException(409, '绑定已变化，请重新核对')
                    content = g['resource'](c, pid, rid, 'content')
                    # Recovered receipt proves the submitted snapshot, even if the local revision changed.
                    local_current = content['revision'] == job['revision']
                    job.update(status='synced', media_id=media_id, error='', synced_at=g['now'](),
                               reconciled=True, local_revision_current=local_current)
                    g['put'](c, pid, 'wechat_draft', job, jid)
                    g['event'](c, pid, actor['user_id'], '核对公众号草稿回执', rid + ' · v' + str(job['revision']))
                return job
            except WechatError as exc:
                raise HTTPException(409, str(exc)) from None
