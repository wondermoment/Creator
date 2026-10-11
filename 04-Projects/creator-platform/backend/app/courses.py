"""Local course publishing; not a paid access-control system."""
import json
from typing import Literal
from urllib.parse import urlparse
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from . import commerce

router = APIRouter(prefix='/api/courses', dependencies=[Depends(commerce.local_only)])

def initialize():
    with commerce.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS video_courses (id TEXT PRIMARY KEY, body TEXT NOT NULL)')

class Lesson(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)

    @field_validator('url')
    @classmethod
    def video_url(cls, value):
        u = urlparse(value)
        if u.scheme != 'https' or not u.hostname or u.username or u.password:
            raise ValueError('请使用 HTTPS 视频直链')
        return value

class Course(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    teacher: str = Field(min_length=1, max_length=80)
    intro: str = Field(min_length=1, max_length=2000)
    status: Literal['draft', 'published'] = 'draft'
    lessons: list[Lesson] = Field(min_length=1, max_length=100)

@router.get('')
def catalog(admin: bool = False):
    with commerce.connect() as c:
        rows = c.execute('SELECT id, body FROM video_courses ORDER BY rowid DESC').fetchall()
    result = [dict(id=r['id'], **json.loads(r['body'])) for r in rows]
    return result if admin else [r for r in result if r['status'] == 'published']

@router.put('/{cid}')
def save(cid: str, course: Course):
    import uuid
    from fastapi import HTTPException
    try:
        uuid.UUID(cid)
    except ValueError:
        raise HTTPException(422, '无效课程编号')
    with commerce.connect() as c:
        c.execute('INSERT INTO video_courses VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body', (cid, course.model_dump_json()))
    return {'ok': True}
