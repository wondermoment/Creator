"""Independently versioned editorial preferences; never facts or tool authority."""
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from repurpose import FORMATS
import editorial_methods


class FormatPreference(BaseModel):
    version: int = Field(ge=0, strict=True)
    requirements: str = Field(default='', max_length=3000)


def snapshot(g, c, pid, name):
    if name not in FORMATS:
        raise HTTPException(422, '内容形态不存在')
    old = next((x for x in g['items'](c, pid, 'format_skill') if x['format'] == name), {})
    return {'id': 'repurpose_' + name, 'format': name, 'name': FORMATS[name][0],
            'version': old.get('version', 0), 'requirements': old.get('requirements', ''),
            'brief': FORMATS[name][1], 'method': editorial_methods.snapshot('video' if name in ('short_video', 'live') else 'content', name)}


def register(g):
    @g['app'].put('/api/projects/{pid}/format-skills/{name}')
    def save(pid: str, name: str, body: FormatPreference, request: Request):
        with g['db']() as c:
            user, _ = g['scope'](c, request, pid, ['owner', 'editor'])
            current = snapshot(g, c, pid, name)
            if current['version'] != body.version:
                raise HTTPException(409, '此形态的写作要求已更新，请刷新再修改')
            old = next((x for x in g['items'](c, pid, 'format_skill') if x['format'] == name), {})
            history = old.get('history', []) + ([{k: old[k] for k in ('version', 'requirements')}] if old else [])
            value = {'format': name, 'version': body.version + 1, 'requirements': body.requirements.strip(),
                     'history': history, 'updated_by': user['user_id']}
            g['put'](c, pid, 'format_skill', value, old.get('id'))
            g['event'](c, pid, user['user_id'], '修改独立内容写作要求', FORMATS[name][0] + ' · v' + str(value['version']))
            return {'format': name, 'version': value['version'], 'requirements': value['requirements']}
