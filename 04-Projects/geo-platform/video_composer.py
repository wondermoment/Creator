"""Local, tenant-scoped manuscript + media editing and MP4 rendering.

This compositor does not call a generative video, avatar or voice service.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import video_skill_render
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sample_review import require_current_sources


class Scene(BaseModel):
    text: str = Field(min_length=1, max_length=72)
    asset_id: str = Field(default='', max_length=80)
    seconds: int = Field(default=6, ge=3, le=12)
    start: float = Field(default=0, ge=0, le=7200)


class Plan(BaseModel):
    source_id: str = Field(min_length=1, max_length=80)
    source_revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=60)
    aspect: str = 'landscape'
    engine: str = 'local'
    scenes: list[Scene] = Field(min_length=1, max_length=8)
    revision: int = Field(default=0, ge=0)


class RenderRequest(BaseModel):
    revision: int = Field(ge=1)


def font_path():
    candidates = [os.environ.get('GEO_VIDEO_FONT', ''), 'C:/Windows/Fonts/msyh.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    return next((p for p in candidates if p and Path(p).is_file()), '')


def capabilities():
    available = bool(shutil.which('ffmpeg') and shutil.which('ffprobe') and font_path())
    return {'available': available, 'mode': 'local_composition', 'audio': False,
            'engines': video_skill_render.capabilities(),
            'message': '本地素材合成可用 · 无声 MP4' if available else '需安装 FFmpeg / FFprobe 和中文字体后才能合成'}


def media_path(root, pid, asset):
    folder = (root / 'assets' / pid).resolve()
    key = asset.get('storage_key', '')
    path = (folder / key).resolve()
    if not key or not path.is_relative_to(folder) or not path.is_file():
        raise HTTPException(422, '素材文件不存在，请重新选择')
    if asset.get('mime') not in ('image/png', 'image/jpeg', 'image/webp', 'video/mp4'):
        raise HTTPException(422, '镜头仅支持 PNG、JPG、WebP 图片和 MP4 视频')
    if path.stat().st_size > 200 * 1024 * 1024:
        raise HTTPException(422, '单份视频制作素材不能超过 200 MB')
    return path


def run_media(args, folder, timeout=120):
    try:
        return subprocess.run(args, cwd=folder, check=True, capture_output=True, timeout=timeout,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
    except subprocess.TimeoutExpired:
        raise ValueError('素材处理超时，请缩短镜头或更换较小的素材') from None
    except (subprocess.CalledProcessError, OSError):
        raise ValueError('素材无法解码或合成失败，请检查文件后重试') from None


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def render_movie(plan, assets, folder, brand):
    if plan.get('engine', 'local') != 'local':
        return video_skill_render.render(plan, assets, folder, brand)
    from PIL import Image, ImageDraw, ImageFont
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    width, height = {'landscape': (1280, 720), 'portrait': (720, 1280), 'square': (720, 720)}[plan['aspect']]
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    font = font_path()
    if not ffmpeg or not ffprobe or not font:
        raise ValueError('合成环境未就绪，请检查 FFmpeg 与中文字体')
    receipts, segments = [], []
    for i, scene in enumerate(plan['scenes']):
        original, asset = assets[i]
        ext = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'video/mp4': '.mp4'}[asset['mime']]
        local = folder / f'media-{i}{ext}'
        shutil.copyfile(original, local)
        digest = file_digest(local)
        expected = plan.get('media_snapshots', {}).get(scene['asset_id'])
        if expected and digest != expected['sha256']:
            raise ValueError('素材在复制期间已变化，请重新核对并生成')
        receipts.append({'asset_id': scene['asset_id'], 'title': asset['title'],
                         'sha256': digest})
        seconds, video = scene['seconds'], asset['mime'] == 'video/mp4'
        if video:
            probe = json.loads(run_media([ffprobe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
                '-show_entries', 'format=duration', '-of', 'json', local.name], folder, 20))
            duration = float(probe.get('format', {}).get('duration', 0))
            if duration < scene['start'] + seconds:
                raise ValueError(f'镜头 {i+1} 的视频长度不足，请调整起点或时长')
        else:
            with Image.open(local) as image:
                if image.width * image.height > 40_000_000:
                    raise ValueError('图片像素过大，请先压缩素材')
                image.verify()
        band = 232 if width == 1280 else 260
        media_h = height - band
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((0, 0, width, 74), fill=(12, 29, 43, 210))
        small = ImageFont.truetype(font, 23 if width == 1280 else 20)
        draw.text((32, 24), brand[:22] + '  /  演示预览', font=small, fill='white')
        draw.rectangle((0, media_h, width, height), fill='#f7faf9')
        draw.rectangle((32, media_h+28, 38, height-34), fill='#087d64')
        draw.text((58, media_h+22), f'{i+1:02d} / {len(plan["scenes"]):02d}   素材演示 · 待审核', font=small, fill='#087d64')
        # Layout by actual glyph width, so Chinese and Latin captions stay in bounds.
        caption_font = ImageFont.truetype(font, 40 if width == 1280 else 34)
        lines, line = [], ''
        for char in scene['text'].replace('\n', ' '):
            if draw.textlength(line + char, font=caption_font) > width - 110:
                lines.append(line); line = ''
            line += char
        lines.append(line)
        if len(lines) > 4:
            raise ValueError(f'镜头 {i+1} 的字幕过长，请精简重点')
        for n, line in enumerate(lines):
            draw.text((58, media_h + 64 + n*46), line, font=caption_font, fill='#173a47')
        overlay.save(folder / f'overlay-{i}.png')
        inputs = (['-ss', str(scene['start']), '-i', local.name] if video else
                  ['-loop', '1', '-i', local.name])
        filters = (f'[0:v]scale={width}:{media_h}:force_original_aspect_ratio=decrease,'
                   f'pad={width}:{height}:(ow-iw)/2:0:color=0x12232c,setsar=1,fps=25[base];'
                   '[base][1:v]overlay=0:0:format=auto,format=yuv420p[out]')
        segment = f'scene-{i}.mp4'
        run_media([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2',
                   '-protocol_whitelist', 'file,pipe', *inputs, '-i', f'overlay-{i}.png',
                   '-filter_complex_threads', '1', '-filter_complex', filters, '-map', '[out]',
                   '-t', str(seconds), '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                   '-crf', '21', '-threads', '2', '-movflags', '+faststart', segment], folder)
        segments.append(segment)
    (folder / 'concat.txt').write_text(''.join(f"file '{s}'\n" for s in segments), encoding='utf-8')
    run_media([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '1',
               '-i', 'concat.txt', '-c', 'copy', '-movflags', '+faststart', 'preview.mp4'], folder)
    return {'width': width, 'height': height, 'seconds': sum(s['seconds'] for s in plan['scenes']),
            'bytes': (folder / 'preview.mp4').stat().st_size, 'media_snapshots': receipts,
            'sha256': hashlib.sha256((folder / 'preview.mp4').read_bytes()).hexdigest()}


def register(g):
    app, db, scope, resource, items, put, event = (g[k] for k in ('app', 'db', 'scope', 'resource', 'items', 'put', 'event'))
    root = g['DB_PATH'].parent
    pool, capacity = ThreadPoolExecutor(max_workers=1, thread_name_prefix='video-compose'), threading.BoundedSemaphore(3)

    def current_source(c, pid, data):
        source = resource(c, pid, data['source_id'], 'content')
        if source.get('revision') != data['source_revision']:
            raise HTTPException(409, '原稿已更新，请重新载入原稿并核对镜头')
        if not source.get('body') or source.get('status') == 'generating':
            raise HTTPException(422, '请先选择有正文的原稿')
        if data.get('source_snapshot') and data['source_snapshot'] != source_info(source):
            raise HTTPException(409, '原稿内容已变化，请重新载入并核对镜头')
        # Pending facts may be reviewed locally, but changed evidence cannot be
        # presented as the same current manuscript or downloadable video.
        require_current_sources(g, c, pid, source)
        return source

    def validate(c, pid, data, require_media=False):
        source = current_source(c, pid, data)
        if data.get('engine', 'local') not in ('local', 'remotion', 'hyperframes'):
            raise HTTPException(422, '不支持此渲染引擎')
        if data['aspect'] not in ('landscape', 'portrait', 'square'):
            raise HTTPException(422, '不支持此画幅')
        if not data['title'].strip() or any(not s['text'].strip() for s in data['scenes']):
            raise HTTPException(422, '请填写视频标题与每个镜头的重点文案')
        for scene in data['scenes']:
            if not scene.get('asset_id'):
                if require_media:
                    raise HTTPException(422, '请为每个镜头选择素材后再生成视频；制作稿可以先保存')
                continue
            media_path(root, pid, resource(c, pid, scene['asset_id'], 'asset'))
        return source

    def source_info(source):
        return {'title': source['title'], 'revision': source['revision'],
                'body_sha256': hashlib.sha256(source['body'].encode()).hexdigest()}

    @app.get('/api/projects/{pid}/video-composer')
    def listing(pid: str, request: Request):
        with db() as c:
            scope(c, request, pid)
            plans, renders = items(c, pid, 'video_plan'), items(c, pid, 'video_render')
            for obj in [*plans, *renders]:
                try:
                    current_source(c, pid, obj.get('plan_snapshot', obj))
                    obj['source_outdated'] = False
                except HTTPException:
                    obj['source_outdated'] = True
            return {'capabilities': capabilities(), 'plans': plans, 'renders': renders}

    @app.post('/api/projects/{pid}/video-composer/plans')
    def create(pid: str, body: Plan, request: Request):
        with db() as c:
            user, _ = scope(c, request, pid, ['owner', 'editor'])
            data = body.model_dump(); source = validate(c, pid, data)
            data.update(revision=1, source_snapshot=source_info(source), created_by=user['user_id'])
            rid = put(c, pid, 'video_plan', data)
            event(c, pid, user['user_id'], '保存视频制作稿', data['title'])
            return {'id': rid, **data}

    @app.put('/api/projects/{pid}/video-composer/plans/{rid}')
    def update(pid: str, rid: str, body: Plan, request: Request):
        with db() as c:
            user, _ = scope(c, request, pid, ['owner', 'editor'])
            old = resource(c, pid, rid, 'video_plan'); g['check_revision'](old, body.revision)
            data = body.model_dump(); source = validate(c, pid, data)
            data.update(revision=old['revision']+1, source_snapshot=source_info(source), created_by=old['created_by'])
            put(c, pid, 'video_plan', data, rid)
            event(c, pid, user['user_id'], '修改视频制作稿', data['title']+' · v'+str(data['revision']))
            return {'id': rid, **data}

    def require_render_actor(c, pid, job):
        member = c.execute('SELECT role FROM members WHERE project_id=? AND user_id=?',
                           (pid, job.get('created_by'))).fetchone()
        if not member or member['role'] not in ('owner', 'editor'):
            raise HTTPException(409, '视频任务发起人的编辑权限已失效，请由有权限的成员核对后重试')

    def media_snapshots(c, pid, plan):
        snapshots = {}
        for aid in dict.fromkeys(scene['asset_id'] for scene in plan['scenes']):
            asset = resource(c, pid, aid, 'asset')
            path = media_path(root, pid, asset)
            try:
                digest = file_digest(path)
            except OSError:
                raise HTTPException(409, '素材无法读取，请核对后重新生成') from None
            if asset.get('sha256') and asset['sha256'] != digest:
                raise HTTPException(409, '素材文件与图库记录不一致，请重新上传并选择素材')
            snapshots[aid] = {k: asset.get(k, '') for k in ('title', 'mime', 'storage_key')}
            snapshots[aid]['sha256'] = digest
        return snapshots

    def require_render_media(c, pid, plan):
        if not plan.get('media_snapshots') or media_snapshots(c, pid, plan) != plan['media_snapshots']:
            raise HTTPException(409, '视频素材已变化，请核对素材后重新生成')

    def execute(pid, rid):
        try:
            with db() as c:
                job = resource(c, pid, rid, 'video_render')
                require_render_actor(c, pid, job)
                current_source(c, pid, job['plan_snapshot'])
                require_render_media(c, pid, job['plan_snapshot'])
                job.update(status='running', error=''); put(c, pid, 'video_render', job, rid)
                assets = []
                for scene in job['plan_snapshot']['scenes']:
                    asset = resource(c, pid, scene['asset_id'], 'asset')
                    assets.append((media_path(root, pid, asset), asset))
            result = render_movie(job['plan_snapshot'], assets, root/'video-renders'/pid/rid, job['brand'])
            with db() as c:
                job = resource(c, pid, rid, 'video_render')
                require_render_actor(c, pid, job)
                current_source(c, pid, job['plan_snapshot'])
                require_render_media(c, pid, job['plan_snapshot'])
                job.update(status='succeeded', result=result, finished_at=g['now']())
                put(c, pid, 'video_render', job, rid)
        except Exception as exc:
            error = str(exc) if isinstance(exc, ValueError) else (exc.detail if isinstance(exc, HTTPException) else '视频合成失败，请检查素材后重试')
            with db() as c:
                job = resource(c, pid, rid, 'video_render')
                job.update(status='failed', error=error, finished_at=g['now']())
                put(c, pid, 'video_render', job, rid)
        finally:
            capacity.release()

    @app.post('/api/projects/{pid}/video-composer/plans/{rid}/render')
    def render(pid: str, rid: str, body: RenderRequest, request: Request):
        acquired = False
        try:
            with db() as c:
                user, _ = scope(c, request, pid, ['owner', 'editor'])
                plan = resource(c, pid, rid, 'video_plan'); g['check_revision'](plan, body.revision)
                validate(c, pid, plan, require_media=True)
                plan['media_snapshots'] = media_snapshots(c, pid, plan)
                existing = next((j for j in items(c, pid, 'video_render') if j['plan_id']==rid and
                    j['plan_revision']==body.revision and j['status'] in ('queued','running','succeeded') and
                    j['plan_snapshot'].get('media_snapshots') == plan['media_snapshots']), None)
                if existing: return existing
                if not capabilities()['available']: raise HTTPException(503, capabilities()['message'])
                engine = plan.get('engine', 'local')
                if engine != 'local' and not any(x['id']==engine and x['available'] for x in video_skill_render.capabilities()):
                    raise HTTPException(503, '所选动画引擎未就绪，请检查本机依赖')
                if not capacity.acquire(blocking=False): raise HTTPException(429, '本机视频合成队列已满，请稍后重试')
                acquired = True
                project = c.execute('SELECT name FROM projects WHERE id=?', (pid,)).fetchone()
                job = {'plan_id': rid, 'plan_revision': plan['revision'], 'plan_snapshot': plan,
                       'source_id': plan['source_id'], 'source_revision': plan['source_revision'],
                       'brand': project['name'], 'status': 'queued', 'error': '', 'created_by': user['user_id']}
                jid = put(c, pid, 'video_render', job)
                event(c, pid, user['user_id'], '生成本地演示视频', plan['title'])
            pool.submit(execute, pid, jid)
            acquired = False
            return {'id': jid, **job}
        finally:
            if acquired: capacity.release()

    @app.get('/api/projects/{pid}/video-composer/renders/{rid}/file')
    def download(pid: str, rid: str, request: Request, download: bool = False):
        with db() as c:
            scope(c, request, pid)
            job = resource(c, pid, rid, 'video_render')
            path = root/'video-renders'/pid/job['id']/'preview.mp4'
            if job['status'] != 'succeeded' or not path.is_file():
                raise HTTPException(404, '视频尚未完成或文件已丢失，请重新生成')
            current_source(c, pid, job['plan_snapshot'])
        # The pinned Starlette version does not implement byte ranges. Browsers
        # need ranges to seek through larger local MP4 previews.
        requested = request.headers.get('range')
        size = path.stat().st_size
        if requested and not download:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not match or not any(match.groups()):
                raise HTTPException(416, '无效视频范围', headers={'Content-Range': f'bytes */{size}'})
            left, right = match.groups()
            start = int(left) if left else max(0, size-int(right))
            end = min(int(right), size-1) if left and right else size-1
            if start > end or start >= size or (not left and int(right) == 0):
                raise HTTPException(416, '视频范围超出文件', headers={'Content-Range': f'bytes */{size}'})
            def chunks():
                with path.open('rb') as file:
                    file.seek(start); remaining = end-start+1
                    while remaining:
                        chunk = file.read(min(65536, remaining))
                        if not chunk: break
                        remaining -= len(chunk)
                        yield chunk
            return StreamingResponse(chunks(), status_code=206, media_type='video/mp4',
                headers={'Cache-Control':'no-store','Accept-Ranges':'bytes',
                         'Content-Range':f'bytes {start}-{end}/{size}','Content-Length':str(end-start+1)})
        return FileResponse(path, media_type='video/mp4', filename='演示视频.mp4',
                            content_disposition_type='attachment' if download else 'inline',
                            headers={'Cache-Control': 'no-store', 'Accept-Ranges':'bytes'})

    @app.on_event('startup')
    def recover():
        with db() as c:
            rows = c.execute("SELECT id,project_id,data FROM resources WHERE kind='video_render'").fetchall()
            for row in rows:
                job = json.loads(row['data'])
                if job['status'] in ('queued', 'running'):
                    job.update(status='failed', error='服务重启中断合成，请核对制作稿后重试')
                    put(c, row['project_id'], 'video_render', job, row['id'])

    return {'execute': execute, 'recover': recover}
