"""Local operator inbox and sanitized product imagery; no external delivery."""
import io
import json
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict, field_validator
from PIL import Image, ImageOps, UnidentifiedImageError
from . import commerce

router = APIRouter(prefix='/api/commerce', dependencies=[Depends(commerce.local_only)])

def initialize():
    with commerce.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS product_images(id TEXT PRIMARY KEY, data BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS service_requests(id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, subject TEXT, kind TEXT, need TEXT, status TEXT, timeline TEXT, created_at TEXT);
        ''')

@router.post('/products/{pid}/image')
async def upload_image(pid: str, file: UploadFile = File(...)):
    with commerce.connect() as c:
        if not c.execute('SELECT 1 FROM shop_content WHERE id=?', (pid,)).fetchone():
            raise HTTPException(404, '请先保存商品，再上传图片')
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, '图片请小于 5 MB')
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > 20000000:
                raise ValueError()
            im = ImageOps.exif_transpose(source).convert('RGB')
            im.thumbnail((1400, 1400))
            out = io.BytesIO()
            im.save(out, format='JPEG', quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, '请上传有效的 JPG、PNG 或 WebP 图片（不超过 2000 万像素）')
    with commerce.connect() as c:
        c.execute('INSERT INTO product_images VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (pid, out.getvalue()))
    return {'ok': True}

@router.get('/products/{pid}/image')
def product_image(pid: str):
    with commerce.connect() as c:
        row = c.execute('SELECT data FROM product_images WHERE id=?', (pid,)).fetchone()
    if not row:
        raise HTTPException(404, '尚未上传图片')
    return Response(row['data'], media_type='image/jpeg', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

class Inquiry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: uuid.UUID
    subject: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=60)
    need: str = Field(min_length=1, max_length=600)

    @field_validator('subject', 'kind', 'need')
    @classmethod
    def trim(cls, value):
        if not value.strip():
            raise ValueError('请填写咨询内容')
        return value.strip()

@router.post('/inquiries')
def submit_inquiry(body: Inquiry):
    with commerce.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        old = c.execute('SELECT * FROM service_requests WHERE request_key=?', (str(body.request_key),)).fetchone()
        if old:
            if any(old[k] != getattr(body, k) for k in ('subject', 'kind', 'need')):
                raise HTTPException(409, '此次请求已提交，请重新打开咨询窗口')
            return {'id': old['id'], 'status': old['status']}
        rid, at = str(uuid.uuid4()), commerce.stamp()
        timeline = [{'status': 'pending', 'note': '已进入本机后台待处理列表', 'at': at}]
        c.execute('INSERT INTO service_requests VALUES (?,?,?,?,?,?,?,?)', (rid, str(body.request_key), body.subject, body.kind, body.need, 'pending', json.dumps(timeline, ensure_ascii=False), at))
    return {'id': rid, 'status': 'pending'}

@router.get('/inquiries')
def inquiries():
    with commerce.connect() as c:
        rows = [dict(r) for r in c.execute('SELECT id,subject,kind,need,status,timeline,created_at FROM service_requests ORDER BY created_at DESC')]
    for r in rows:
        r['timeline'] = json.loads(r['timeline'])
    return rows

class Followup(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['pending', 'following', 'closed']
    expected_version: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=1000)

@router.patch('/inquiries/{rid}')
def followup(rid: str, body: Followup):
    if not body.note.strip():
        raise HTTPException(422, '请填写给客户的进度说明')
    with commerce.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM service_requests WHERE id=?', (rid,)).fetchone()
        if not row:
            raise HTTPException(404, '咨询不存在')
        timeline = json.loads(row['timeline'])
        if len(timeline) != body.expected_version:
            raise HTTPException(409, '进度已更新，请关闭窗口并刷新列表后重试')
        if body.status == 'pending' or (row['status'] == 'pending' and body.status == 'closed'):
            raise HTTPException(422, '请先受理跟进，再完成咨询')
        timeline.append({'status': body.status, 'note': body.note.strip(), 'at': commerce.stamp()})
        c.execute('UPDATE service_requests SET status=?,timeline=? WHERE id=?', (body.status, json.dumps(timeline, ensure_ascii=False), rid))
    return {'ok': True}
