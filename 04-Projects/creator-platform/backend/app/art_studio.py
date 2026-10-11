"""Local creative studio; generation goes to MuAPI only after explicit submission."""
import json
import os
import uuid
from urllib.parse import urlparse, quote
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from . import commerce

router = APIRouter(prefix='/api/art', dependencies=[Depends(commerce.local_only)])
BASE = 'https://api.muapi.ai/api/v1'

def initialize():
    with commerce.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS art_jobs(id TEXT PRIMARY KEY,kind TEXT,prompt TEXT,status TEXT,remote_id TEXT,outputs TEXT,created_at TEXT)')

class Creation(BaseModel):
    request_key: uuid.UUID
    kind: Literal['music', 'painting', 'collage']
    prompt: str = Field(min_length=3, max_length=1200)
    consent: Literal[True]

def key():
    value = os.getenv('MUAPI_KEY')
    if not value:
        raise HTTPException(503, '生成服务尚未配置，请稍后再试')
    return value

def public(row):
    d = dict(row)
    d.pop('remote_id', None)
    d['outputs'] = json.loads(d['outputs'])
    return d

@router.get('/works')
def works():
    with commerce.connect() as c:
        return [public(r) for r in c.execute('SELECT * FROM art_jobs ORDER BY created_at DESC LIMIT 40')]

@router.post('/create')
async def create(body: Creation):
    token = key()
    rid = str(body.request_key)
    with commerce.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        old = c.execute('SELECT * FROM art_jobs WHERE id=?', (rid,)).fetchone()
        if old:
            if old['prompt'] != body.prompt or old['kind'] != body.kind:
                raise HTTPException(409, '请重新打开创作页后提交')
            return public(old)
        active = c.execute("SELECT count(*) FROM art_jobs WHERE status IN ('submitting','processing')").fetchone()[0]
        if active >= 3:
            raise HTTPException(429, '已有创作正在生成，请先到我的作品查看进度')
        c.execute('INSERT INTO art_jobs VALUES (?,?,?,?,?,?,?)', (rid, body.kind, body.prompt, 'submitting', None, '[]', commerce.stamp()))
    if body.kind == 'music':
        endpoint = '/suno-create-music'
        payload = {'style': 'Gentle instrumental ambient, soft piano, even dynamics, no sudden loud sounds. ' + body.prompt, 'prompt': body.prompt, 'model': 'V5', 'instrumental': True, 'duration': 60}
    else:
        endpoint = '/flux-dev-image'
        payload = {'prompt': ('Paper collage, tactile paper shapes, gentle colors. ' if body.kind == 'collage' else 'Expressive watercolor illustration, gentle colors. ') + body.prompt + '. No text, no watermark.', 'width': 768, 'height': 1024, 'num_images': 1}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(BASE + endpoint, headers={'x-api-key': token}, json=payload)
        if response.status_code >= 400:
            with commerce.connect() as c:
                c.execute("UPDATE art_jobs SET status='failed' WHERE id=?", (rid,))
            raise HTTPException(502, '生成服务密钥无效，请由运营更新配置后重试' if response.status_code in (401,403) else '生成服务未接受任务，请检查服务额度或稍后再试')
        remote = response.json().get('request_id')
        if not remote:
            raise ValueError('missing request id')
        with commerce.connect() as c:
            c.execute("UPDATE art_jobs SET status='processing',remote_id=? WHERE id=?", (str(remote), rid))
    except (httpx.HTTPError, ValueError):
        with commerce.connect() as c:
            c.execute("UPDATE art_jobs SET status='uncertain' WHERE id=?", (rid,))
        raise HTTPException(502, '提交结果暂不明确，请勿重复生成，联系运营核对任务与费用')
    return {'id': rid, 'status': 'processing', 'outputs': []}

def media_urls(value):
    result = []
    if isinstance(value, str):
        p = urlparse(value)
        if p.scheme == 'https' and p.hostname and not p.username:
            result.append(value)
    elif isinstance(value, list):
        for x in value:
            result.extend(media_urls(x))
    elif isinstance(value, dict):
        for k in ('url', 'audio_url', 'image_url', 'outputs'):
            if k in value:
                result.extend(media_urls(value[k]))
    return list(dict.fromkeys(result))[:4]

@router.get('/works/{rid}')
async def refresh(rid: str):
    with commerce.connect() as c:
        row = c.execute('SELECT * FROM art_jobs WHERE id=?', (rid,)).fetchone()
    if not row:
        raise HTTPException(404, '作品不存在')
    if row['status'] == 'processing' and row['remote_id']:
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                response = await client.get(BASE+'/predictions/'+quote(row['remote_id'], safe='')+'/result', headers={'x-api-key': key()})
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, '进度暂时不可用，作品任务已保留，请稍后刷新')
        status = data.get('status')
        if status in ('completed', 'failed'):
            outputs = media_urls(data.get('outputs', [])) if status == 'completed' else []
            with commerce.connect() as c:
                c.execute('UPDATE art_jobs SET status=?,outputs=? WHERE id=?', ('completed' if outputs else 'failed', json.dumps(outputs), rid))
    with commerce.connect() as c:
        return public(c.execute('SELECT * FROM art_jobs WHERE id=?', (rid,)).fetchone())
