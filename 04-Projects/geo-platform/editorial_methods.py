"""Reviewed editorial rules, frozen with each job; source corpus is never executed."""
from pathlib import Path
from hashlib import sha256

ROOT = Path(__file__).parent / 'skills' / 'industrial-content'
ROLES = {'strategist': '策略顾问', 'content': '内容策划', 'technical': '技术写作',
         'seo_editor': 'SEO/GEO编辑', 'video': '视频脚本', 'reviewer': '内容审核'}
FILES = {'article': 'long-article', 'xiaohongshu': 'xiaohongshu', 'greenbook': 'wechat-note',
         'moments': 'moments', 'community': 'community', 'sales': 'sales-chat',
         'short_video': 'short-video', 'live': 'livestream'}


def snapshot(role, format_name=''):
    shared = (ROOT / 'SKILL.md').read_text(encoding='utf-8').split('## 1.')[1].split('## 3.')[0]
    roles = (ROOT / 'references' / 'expert-roles.md').read_text(encoding='utf-8')
    selected = next((line for line in roles.splitlines() if '**' + ROLES[role] + '**' in line), '')
    form = ((ROOT / 'references' / (FILES[format_name] + '.md')).read_text(encoding='utf-8')
            if format_name in FILES else '')
    text = '工业内容论证方法\n## 1.' + shared + '\n本角色职责：\n' + selected + '\n' + form
    text += '\n不可将盐雾测试小时直接换算实际使用寿命；实验条件与现场变量须分别说明。'
    return {'version': '2026-10-05.1', 'sha256': sha256(text.encode()).hexdigest(),
            'reference': 'https://www.hqhf.com', 'rules': text}
