"""Local GEO delivery MVP. Tenant authorization is enforced on every resource route."""
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import threading
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('GEO_DB_PATH', ROOT / '.runtime' / 'geo.db'))
CHANNEL_CATALOG = [
    {'name': '企业官网', 'label': '中英文官网 / WordPress', 'priority': 'P0', 'purpose': '产品、参数、选型、案例、英文资料', 'adapter': '正式 CMS API 优先', 'formats': ['图文'], 'acceptance': '核验 CMS 权限、草稿、图片上传、发布与 URL 回执'},
    {'name': '微信公众号', 'priority': 'P0', 'purpose': '技术长文、案例、客户培育', 'adapter': '正式草稿 / 发布 API；浏览器草稿备选', 'formats': ['图文'], 'acceptance': '逐账号核对资质及接口权限；草稿与最终发布分开验收'},
    {'name': '知乎', 'priority': 'P0', 'purpose': '选型、工况、方案比较', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；先验草稿与最终发布，尚未实测'},
    {'name': '百家号', 'priority': 'P0', 'purpose': '产品应用、技术解释', 'adapter': 'Wechatsync 候选', 'formats': ['图文', '视频'], 'acceptance': '用户提供声明图文支持；图文与视频分别验收'},
    {'name': '搜狐号', 'priority': 'P1', 'purpose': '品牌与应用文章', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；适配器尚未实测'},
    {'name': '头条号', 'priority': 'P1', 'purpose': '行业知识、生产过程', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；适配器尚未实测'},
    {'name': '网易号', 'priority': 'P1', 'purpose': '品牌与行业内容', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；适配器尚未实测'},
    {'name': '列举网', 'label': '列举网 / B2B', 'priority': 'P1', 'purpose': '产品、应用方案与企业供求信息', 'adapter': '浏览器登录与发布流程待验证', 'formats': ['图文'], 'acceptance': '注册页实测需要手机号、拼图验证及短信验证码；草稿保存与发布能力待登录后核验', 'register_url': 'https://www.lieju.com/reg/'},
    {'name': 'CSDN', 'priority': '按行业', 'purpose': '工业软件、嵌入式、工业通信、算法', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；仅为相关产品启用'},
    {'name': '哔哩哔哩', 'label': 'Bilibili / 哔哩哔哩', 'priority': '按受众', 'purpose': '设备演示、测试、安装、维护', 'adapter': '专栏：Wechatsync；视频：social-auto-upload 候选', 'formats': ['专栏', '视频'], 'acceptance': '专栏与视频分别验收，不把文章能力算作视频能力'},
    {'name': '小红书', 'priority': '按受众', 'purpose': '可视化产品、工厂故事、设计应用', 'adapter': '待选型 / 人工发布包', 'formats': ['图文', '视频'], 'acceptance': '图文与视频分开验收，按受众匹配启用'},
    {'name': '抖音', 'priority': '按受众', 'purpose': '工厂、工艺、设备演示', 'adapter': 'social-auto-upload 视频候选', 'formats': ['图文', '视频'], 'acceptance': '视频候选适配器待实测；图文另行核验'},
    {'name': '简书', 'priority': '低优先级', 'purpose': '可选图文扩展', 'adapter': 'Wechatsync 候选', 'formats': ['图文'], 'acceptance': '用户提供声明支持；低于核心行业渠道'},
    {'name': '视频号', 'priority': '扩展', 'purpose': '客户培育、设备演示、直播素材', 'adapter': 'social-auto-upload 候选', 'formats': ['视频'], 'acceptance': '账号登录、素材、审核、发布和回执逐项确认'},
    {'name': 'LinkedIn', 'priority': '海外', 'purpose': '海外决策者、英文品牌内容', 'adapter': 'Postiz 候选', 'formats': ['图文'], 'acceptance': '账号授权、API 权限及平台审批逐项确认'},
    {'name': 'YouTube', 'priority': '海外', 'purpose': '海外技术演示、设备操作', 'adapter': 'Postiz 候选', 'formats': ['视频'], 'acceptance': '账号授权、API 权限及平台审批逐项确认'},
    {'name': 'X', 'priority': '海外', 'purpose': '海外品牌内容与技术动态', 'adapter': 'Postiz 候选', 'formats': ['图文'], 'acceptance': '账号授权、API 权限及平台审批逐项确认'},
    {'name': '行业媒体', 'priority': '按项目', 'purpose': '行业信源与付费媒介组合', 'adapter': '人工交付 / 媒介服务商待选', 'formats': ['图文'], 'acceptance': '单独记录价格、版位和回执；不承诺 AI 引用'}
]
CHANNELS = [c['name'] for c in CHANNEL_CATALOG]
LOGIN_URLS = {
    '网易号': 'https://mp.163.com/login.html', '搜狐号': 'https://mp.sohu.com/mpfe/v4/login',
    '百家号': 'https://baijiahao.baidu.com/builder/theme/bjh/login', '头条号': 'https://mp.toutiao.com/auth/page/login',
    '列举网': 'https://www.lieju.com/login/', '知乎': 'https://www.zhihu.com/signin',
    '哔哩哔哩': 'https://passport.bilibili.com/login', 'CSDN': 'https://www.csdn.net/',
    '小红书': 'https://creator.xiaohongshu.com/login?source=official', '抖音': 'https://creator.douyin.com',
    '简书': 'https://www.jianshu.com/sign_in', '微信公众号': 'https://mp.weixin.qq.com/cgi-bin/loginpage'
}
for channel in CHANNEL_CATALOG:
    channel['login_url'] = LOGIN_URLS.get(channel['name'], '')
PLATFORMS = ['豆包', '腾讯元宝', 'Kimi', 'DeepSeek', 'ChatGPT', 'Claude', 'Grok']
BASE_SKILLS = [
    {'id': 'product', 'name': '产品与应用方案', 'version': 1, 'description': '将产品事实整理为应用说明，保留使用条件。', 'prompt': '面向 B2B 采购与工程人员，按照问题、适用场景、产品事实、使用条件、验证建议组织内容。不得补造参数、资质或效果。'},
    {'id': 'faq', 'name': '采购问题与选型指南', 'version': 1, 'description': '从客户问题出发，解释选型和验证路径。', 'prompt': '先直接回应问题，再列出选择标准和待确认条件。用知识库来源支撑事实；信息不足时明确待补充，不虚构竞品比较。'},
    {'id': 'video', 'name': '工厂与产品视频脚本', 'version': 1, 'description': '用企业已有素材规划镜头、口播与字幕。', 'prompt': '输出开场问题、产品实拍、应用条件、验证过程和咨询引导五个镜头。只引用已确认事实，不生成虚假的测试或客户见证。'},
    {'id':'strategy','name':'企业 GEO 内容策略','version':1,'description':'受众、问题簇、证据缺口和内容计划。','prompt':'依据当前企业资料和历史需求，输出目标受众、采购阶段、问题簇、内容优先级、所需事实、交付人与验收指标。区分假设和已有证据，不编造搜索量或传播效果。'},
    {'id':'geo_audit','name':'GEO 证据诊断','version':1,'description':'核对真实回答、提及和引用，形成改进清单。','prompt':'先核对平台、问题、采样时间与来源。区分品牌提及、品牌推荐、任意引用和本企业引用，不用模型API替代消费者App。输出观察、依据、局限、待补证据、优先行动和复测方法。网站就绪度不等于实际引用表现。'},
    {'id':'reference_analysis','name':'参考内容八维拆解','version':1,'description':'提炼文章和字幕的方法，保留出处后复用。','prompt':'学习参考材料的受众切入、开篇、结构、论证、结尾和表达方式。保留原始来源和可验证短片段。只提炼方法，不将对方事实套到本企业，不承诺爆款或流量。'}
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid():
    return secrets.token_hex(12)


def dump(data):
    return json.dumps(data, ensure_ascii=False)


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, identity TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, website TEXT NOT NULL, questions TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS members(project_id TEXT NOT NULL REFERENCES projects(id), user_id TEXT NOT NULL REFERENCES users(id), role TEXT NOT NULL, PRIMARY KEY(project_id,user_id));
        CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), kind TEXT NOT NULL, data TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS resource_scope ON resources(project_id,kind);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), actor TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_limits(bucket TEXT PRIMARY KEY, hits INTEGER NOT NULL, window TEXT NOT NULL);
        ''')


init_db()
app = FastAPI(title='品牌铸匠 GEO · 企业交付工作台', docs_url='/api/docs')


@app.middleware('http')
async def security(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and urlparse(origin).netloc != request.headers.get('host'):
            return Response('Cross-origin request rejected', 403)
    result = await call_next(request)
    result.headers['X-Content-Type-Options'] = 'nosniff'
    result.headers['X-Frame-Options'] = 'DENY'
    result.headers['Referrer-Policy'] = 'same-origin'
    result.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api'):
        result.headers['Cache-Control'] = 'no-store'
    return result


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
    return salt + ':' + derived


def identity_value(raw):
    value = raw.strip().lower()
    if not (re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) or re.fullmatch(r'\+?[0-9]{8,15}', value)):
        raise HTTPException(422, '请输入有效邮箱或手机号')
    return value


def current(c, req):
    token = req.cookies.get('geo_session', '')
    row = c.execute('SELECT s.*,u.identity FROM sessions s JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), now())).fetchone()
    if not row:
        raise HTTPException(401, '请先登录')
    if req.method not in ('GET', 'HEAD') and not hmac.compare_digest(req.headers.get('x-csrf-token', ''), row['csrf']):
        raise HTTPException(403, '会话校验失败，请刷新页面')
    return row


def scope(c, req, pid, roles=None):
    user = current(c, req)
    member = c.execute('SELECT role FROM members WHERE project_id=? AND user_id=?', (pid, user['user_id'])).fetchone()
    if not member:
        raise HTTPException(404, '企业空间不存在或无访问权限')
    if roles and member['role'] not in roles:
        raise HTTPException(403, '当前角色无权执行此操作')
    return user, member['role']


def prompt_admin(user):
    try:
        allowed = json.loads((DB_PATH.parent / 'prompt-admins.json').read_text(encoding='utf-8'))
        return isinstance(allowed, list) and user['user_id'] in allowed
    except (OSError, ValueError): return False


def require_prompt_admin(c, request, pid):
    user, role = scope(c, request, pid)
    if not prompt_admin(user): raise HTTPException(403, '仅技术管理后台可访问核心提示词配置')
    return user, role


@app.get('/admin')
def admin_page():
    return FileResponse(ROOT / 'static' / 'admin.html')


@app.get('/api/projects/{pid}/admin-config')
def admin_config(pid: str, request: Request):
    with db() as c:
        require_prompt_admin(c, request, pid)
        return {'agents':[agent_soul(c,pid,a) for a in AGENT_ROLES],
                'skills':[next((x for x in items(c,pid,'skill') if x['base_id']==base['id']),base) for base in BASE_SKILLS]}


def public_records(value, user):
    if prompt_admin(user): return value
    hidden = {'prompt', 'prompt_snapshot', 'prompt_override', 'markdown', 'soul', 'soul_markdown'}
    # Resolve permission once per response, not once per nested field. Keep it
    # request-local so permission revocation takes effect on the next call.
    def redact(item):
        if isinstance(item, dict): return {k:redact(v) for k,v in item.items() if k not in hidden}
        if isinstance(item, list): return [redact(v) for v in item]
        return item
    return redact(value)


def resource(c, pid, rid, kind=None):
    row = c.execute('SELECT * FROM resources WHERE project_id=? AND id=?', (pid, rid)).fetchone()
    if not row or (kind and row['kind'] != kind):
        raise HTTPException(404, '记录不存在')
    return {'id': row['id'], 'kind': row['kind'], 'created': row['created'], 'updated': row['updated'], **json.loads(row['data'])}


def items(c, pid, kind):
    return [{'id': r['id'], 'kind': r['kind'], 'created': r['created'], 'updated': r['updated'], **json.loads(r['data'])} for r in c.execute('SELECT * FROM resources WHERE project_id=? AND kind=? ORDER BY created DESC,rowid DESC', (pid, kind))]


def knowledge_usable(c, pid, doc, require_confirmed=True, seen=None):
    """Check FAQ and derived evidence transitively, including legacy records."""
    seen = set(seen or ())
    if doc['id'] in seen or len(seen) >= 100 or doc.get('knowledge_outdated'):
        return False
    if require_confirmed and doc['status'] != 'confirmed':
        return False
    seen.add(doc['id'])
    faq = next((f for f in items(c, pid, 'faq') if f['knowledge_id'] == doc['id']), None)
    snapshots = list((faq or {}).get('source_snapshots', []))
    if doc.get('derived') or doc.get('source_ids') or doc.get('source_snapshots'):
        derived_sources = doc.get('source_snapshots')
        # Never infer historic provenance from the sources' current versions.
        if not isinstance(derived_sources, list) or not derived_sources:
            return False
        if any(not isinstance(s, dict) or not s.get('id') or type(s.get('version')) is not int for s in derived_sources):
            return False
        if set(doc.get('source_ids', [])) != {s['id'] for s in derived_sources}:
            return False
        snapshots.extend(derived_sources)
    for snapshot in snapshots:
        try:
            source = resource(c, pid, snapshot['id'], 'knowledge')
        except HTTPException:
            return False
        if source['version'] != snapshot['version'] or not knowledge_usable(c, pid, source, seen=seen):
            return False
    return True


def knowledge_review_summary(c, pid, doc):
    """Read-only presentation: historic confirmation never implies current validity."""
    source_valid = knowledge_usable(c, pid, doc, require_confirmed=False)
    effective = source_valid and doc['status'] == 'confirmed'
    digest = hashlib.sha256(doc['body'].encode('utf-8')).hexdigest()
    history = []
    for entry in doc.get('confirmation_history', []):
        current_version = entry.get('version') == doc['version']
        if not current_version:
            label = '历史版本确认'
        elif entry.get('body_sha256') != digest:
            label = '当前版本记录校验值不匹配'
        else:
            label = '当前版本确认' if effective else '当前版本确认已失效'
        history.append({key: entry.get(key, '') for key in ('version', 'actor', 'confirmed_at', 'body_sha256')})
        history[-1]['label'] = label
    return {'effective_confirmed': effective, 'source_valid': source_valid, 'history': history}


def put(c, pid, kind, data, rid=None):
    stamp = now()
    if rid:
        c.execute('UPDATE resources SET data=?,updated=? WHERE project_id=? AND id=? AND kind=?', (dump({k: v for k, v in data.items() if k not in ('id', 'kind', 'created', 'updated')}), stamp, pid, rid, kind))
        return rid
    rid = uid()
    c.execute('INSERT INTO resources VALUES(?,?,?,?,?,?)', (rid, pid, kind, dump(data), stamp, stamp))
    return rid


def event(c, pid, user, action, detail):
    c.execute('INSERT INTO events VALUES(?,?,?,?,?,?)', (uid(), pid, user, action, detail, now()))


def project(c, pid):
    row = dict(c.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone())
    row['questions'] = json.loads(row['questions'])
    row['demo'] = bool(row['demo'])
    return row


def check_url(value):
    if not value:
        return ''
    value = value.strip()
    if not value.startswith(('https://', 'http://')):
        value = 'https://' + value
    parsed = urlparse(value)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, '请输入有效的网站地址')
    return value


class Auth(BaseModel):
    identity: str = Field(min_length=3, max_length=180)
    password: str = Field(min_length=10, max_length=128)


def limit_auth(req):
    bucket = req.client.host if req.client else 'local'
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec='seconds')
    with db() as c:
        row = c.execute('SELECT * FROM auth_limits WHERE bucket=?', (bucket,)).fetchone()
        if row and row['window'] > cutoff and row['hits'] >= 40:
            raise HTTPException(429, '尝试次数过多，请 10 分钟后再试')
        hits = row['hits'] + 1 if row and row['window'] > cutoff else 1
        window = row['window'] if row and row['window'] > cutoff else now()
        c.execute('INSERT OR REPLACE INTO auth_limits VALUES(?,?,?)', (bucket, hits, window))


def login_session(c, user_id, response):
    token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions VALUES(?,?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(timespec='seconds')))
    response.set_cookie('geo_session', token, httponly=True, samesite='strict', max_age=43200, secure=os.environ.get('GEO_SECURE_COOKIE') == '1')
    return {'csrf': csrf}


@app.post('/api/register')
def register(body: Auth, response: Response, request: Request):
    limit_auth(request)
    identity = identity_value(body.identity)
    with db() as c:
        if c.execute('SELECT id FROM users WHERE identity=?', (identity,)).fetchone():
            raise HTTPException(409, '该账号已注册，请登录')
        user_id = uid()
        c.execute('INSERT INTO users VALUES(?,?,?,?)', (user_id, identity, password_hash(body.password), now()))
        return login_session(c, user_id, response)


@app.post('/api/login')
def login(body: Auth, response: Response, request: Request):
    limit_auth(request)
    with db() as c:
        row = c.execute('SELECT * FROM users WHERE identity=?', (identity_value(body.identity),)).fetchone()
        stored = row['password'] if row else password_hash('not-a-real-password')
        matched = hmac.compare_digest(stored, password_hash(body.password, stored.split(':')[0]))
        if not row or not matched:
            raise HTTPException(401, '账号或密码不正确')
        return login_session(c, row['id'], response)


@app.post('/api/logout')
def logout(request: Request, response: Response):
    with db() as c:
        user = current(c, request)
        c.execute('DELETE FROM sessions WHERE token=?', (user['token'],))
    response.delete_cookie('geo_session')
    return {'ok': True}


@app.get('/api/me')
def me(request: Request):
    with db() as c:
        user = current(c, request)
        return {'identity': user['identity'], 'csrf': user['csrf'], 'verified': False, 'can_manage_prompts':prompt_admin(user), 'projects': [dict(r) for r in c.execute('SELECT p.id,p.name,p.website,p.demo,m.role FROM projects p JOIN members m ON m.project_id=p.id WHERE m.user_id=? ORDER BY p.created,p.id', (user['user_id'],))], 'base_skills': public_records(BASE_SKILLS,user), 'channels': CHANNELS, 'channel_catalog': CHANNEL_CATALOG, 'platforms': PLATFORMS}


class ProjectInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    website: str = Field(default='', max_length=500)
    questions: list[str] = Field(min_length=1, max_length=20)


def create_project(c, user_id, name, website, questions, demo=False):
    if any(not q.strip() or len(q) > 300 for q in questions):
        raise HTTPException(422, '问题不能为空，单条限 300 字')
    pid = uid()
    c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?)', (pid, name.strip(), check_url(website), dump(questions), int(demo), now()))
    c.execute('INSERT INTO members VALUES(?,?,?)', (pid, user_id, 'owner'))
    event(c, pid, user_id, '创建企业空间', name)
    return pid


@app.post('/api/projects')
def new_project(body: ProjectInput, request: Request):
    with db() as c:
        user = current(c, request)
        pid = create_project(c, user['user_id'], body.name, body.website, body.questions)
        put(c, pid, 'diagnosis', {'status': 'awaiting_evidence', 'samples': [], 'summary': '首诊已建立。AI 平台采样尚未接通，请录入实际回答和引用证据后查看结果。'})
        return {'id': pid}


@app.post('/api/demo')
def demo(request: Request, response: Response):
    limit_auth(request)
    with db() as c:
        user_id = uid()
        c.execute('INSERT INTO users VALUES(?,?,?,?)', (user_id, 'demo-' + user_id + '@local.example', password_hash(secrets.token_urlsafe(30)), now()))
        pid = create_project(c, user_id, '澄川精工 · 示例', 'https://example.com', ['如何选择精密零部件加工供应商？', '小批量定制加工需要提供哪些资料？', '如何验证零件交付的一致性？'], True)
        create_project(c, user_id, '远山新材 · 示例', 'https://example.org', ['如何评估工业材料的适用性？'], True)
        kid = put(c, pid, 'knowledge', {'title': '企业与产品资料（虚构示例）', 'category': '产品', 'body': '澄川精工是用于演示的虚构企业。示例业务为精密零部件加工，采购沟通资料包括图纸版本、材料要求、尺寸公差、数量和交期。所有能力与案例需由实际企业提供证据。', 'source': '本机示例资料', 'status': 'confirmed', 'version': 1})
        cid = put(c, pid, 'content', {'title': '选择精密加工供应商，先确认这五项资料', 'body': '采购精密加工服务，先把需求说清楚。\n\n1. 图纸与版本：确保双方讨论同一份技术文件。\n2. 材料要求：提供牌号、用途及可接受的替代范围。\n3. 尺寸与公差：标明关键尺寸以及检验要求。\n4. 数量与交期：区分打样和后续批量需求。\n5. 验证方式：约定样件确认和验收资料。\n\n本文为虚构企业的演示草稿，技术内容待企业复核。', 'status': 'pending', 'revision': 1, 'skill_name': '采购问题与选型指南', 'skill_version': 1, 'prompt_snapshot': BASE_SKILLS[1]['prompt'], 'sources': [{'id': kid, 'title': '企业与产品资料（虚构示例）', 'version': 1, 'body': resource(c, pid, kid, 'knowledge')['body']}], 'channels': ['企业官网', '知乎'], 'scheduled': '', 'approved_revision': None, 'review_note': '', 'generator': '示例内容', 'history': []})
        put(c, pid, 'diagnosis', {'status': 'sample', 'summary': '虚构样本，仅展示报告结构，不代表真实 AI 平台结果。', 'samples': [{'question': '如何选择精密零部件加工供应商？', 'platform': p, 'answer': '演示回答；并非真实平台采集。', 'mentioned': i < 2, 'citation': 'https://example.com' if i == 0 else '', 'observed_at': now(), 'source': 'demo'} for i, p in enumerate(PLATFORMS[:5])]})
        put(c, pid, 'lead', {'company': '星港设备（虚构）', 'contact': '演示联系人', 'source': '官网表单 · 示例', 'need': '咨询小批量加工的图纸评估流程', 'status': 'new', 'owner': '待分配', 'note': '', 'content_id': cid})
        event(c, pid, user_id, '导入示例资料', '示例数据仅用于验证流程，不代表经营效果')
        result = login_session(c, user_id, response)
        result['project_id'] = pid
        return result


def content_provenance_valid(c, pid, content):
    # Legacy manuscripts have only knowledge citations, checked by existing
    # gates. Generated expert drafts additionally carry a method/parent trail.
    if not any(content.get(key) for key in ('repurpose_source', 'writing_modules',
                                           'writing_references', 'history_sources', 'history_methods', 'geo_evidence')):
        return True
    return delivery['expert_sources_valid'](c, pid, content)


def require_content_provenance(c, pid, content):
    if not content_provenance_valid(c, pid, content):
        raise HTTPException(409, '原稿或创作依据已变更，请根据最新依据重新创作并审核')


def content_approval_summary(c, pid, content):
    """Project approval validity without rewriting the original review record."""
    reasons = []
    if not sample_review.layout_current(content):
        reasons.append(sample_review.LAYOUT_STALE_MESSAGE)
    outdated = bool(content.get('knowledge_outdated'))
    if outdated:
        reasons.append('引用知识已标记过期')
    if not content_provenance_valid(c, pid, content):
        outdated = True
        reasons.append('原稿或创作依据已变更')
    for snapshot in content.get('sources', []):
        try:
            source = resource(c, pid, snapshot['id'], 'knowledge')
        except HTTPException:
            outdated = True
            reasons.append('引用知识不可用')
            continue
        if source['version'] != snapshot['version']:
            outdated = True
            reasons.append('引用知识版本不一致')
        elif not knowledge_usable(c, pid, source):
            outdated = True
            reasons.append('引用知识未核准或来源已失效')
    if content.get('status') != 'approved':
        reasons.append('当前内容尚未审核通过')
    elif content.get('approved_revision') != content.get('revision'):
        reasons.append('审批版本与当前内容不一致')
    if not content.get('channels'):
        reasons.append('尚未选择发布渠道')
    return {'effective_approved': not reasons, 'sources_outdated': outdated,
            'reasons': list(dict.fromkeys(reasons))}


def stats(c, pid):
    content, pubs, leads, reports = [items(c, pid, k) for k in ['content', 'publication', 'lead', 'diagnosis']]
    samples = reports[0]['samples'] if reports else []
    valid = [s for s in samples if s.get('answer')]
    platform_stats = []
    for platform in PLATFORMS:
        rows = [s for s in valid if s['platform'] == platform]
        platform_stats.append({'name': platform, 'total': len(rows), 'mentions': sum(bool(s['mentioned']) for s in rows)})
    trend = []
    for offset in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
        trend.append({'date': day, 'content': sum(x['created'].startswith(day) for x in content), 'published': sum(x.get('received_at', '').startswith(day) and x['status'] in ('recorded', 'published') for x in pubs), 'leads': sum(x['created'].startswith(day) for x in leads)})
    return {'content': len(content), 'pending': sum(x['status'] == 'pending' for x in content), 'approved': sum(content_approval_summary(c, pid, x)['effective_approved'] for x in content), 'published': sum(x['status'] in ('recorded', 'published') for x in pubs), 'waiting': sum(x['status'] == 'awaiting_connector' for x in pubs), 'leads': len(leads), 'qualified': sum(x['status'] in ['qualified', 'won'] for x in leads), 'samples': len(valid), 'mentions': sum(bool(x['mentioned']) for x in valid), 'citations': sum(bool(x.get('citation')) for x in valid), 'platforms': platform_stats, 'trend': trend, 'updated_at': now()}


@app.get('/api/projects/{pid}/state')
def state(pid: str, request: Request):
    with db() as c:
        user, role = scope(c, request, pid)
        data = {kind: items(c, pid, kind) for kind in ['knowledge', 'skill', 'content', 'publication', 'lead', 'diagnosis', 'channel', 'automation', 'automation_run', 'brand', 'faq', 'asset', 'insight', 'contact_entry', 'comment', 'execution', 'observation', 'seo_audit', 'media_opportunity', 'geo_snapshot', 'import_batch', 'evidence_claim', 'content_reference', 'seo_task']}
        data['user_intent'] = items(c, pid, 'user_intent')
        data['format_skill'] = items(c, pid, 'format_skill')
        for doc in data['knowledge']:
            doc['review_summary'] = knowledge_review_summary(c, pid, doc)
            if not doc['review_summary']['source_valid']:
                doc.update(status='pending', knowledge_outdated=True)
        for content in data['content']:
            content['approval_summary'] = content_approval_summary(c, pid, content)
        data['connector_status'] = [{'provider': x['provider'], 'status': x['status'], 'model': x.get('model', ''), 'verified_at': x.get('verified_at', '')} for x in items(c, pid, 'connector')]
        data.update(project=project(c, pid), role=role, stats=stats(c, pid), events=[dict(r) for r in c.execute('SELECT e.id,u.identity AS actor,e.action,e.detail,e.created FROM events e LEFT JOIN users u ON u.id=e.actor WHERE project_id=? ORDER BY e.created DESC,e.rowid DESC LIMIT 100', (pid,))], members=[dict(r) for r in c.execute('SELECT u.identity,m.role FROM members m JOIN users u ON u.id=m.user_id WHERE project_id=?', (pid,))])
        return public_records(data, user)


@app.get('/api/projects/{pid}/metrics')
def metrics(pid: str, request: Request):
    with db() as c:
        scope(c, request, pid)
        return stats(c, pid)


class KnowledgeInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    category: str = Field(max_length=40)
    body: str = Field(min_length=1, max_length=80000)
    source: str = Field(min_length=1, max_length=500)


class ChannelInput(BaseModel):
    name: str
    enabled: bool
    purpose: str = Field(max_length=1000)
    frequency: str = Field(max_length=100)
    language: str = Field(max_length=50)
    account_label: str = Field(max_length=180)
    note: str = Field(max_length=2000)


@app.post('/api/projects/{pid}/channels')
def configure_channel(pid: str, body: ChannelInput, request: Request):
    if body.name not in CHANNELS:
        raise HTTPException(422, '渠道不存在')
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        previous = next((x for x in items(c, pid, 'channel') if x['name'] == body.name), None)
        rid = put(c, pid, 'channel', {**body.model_dump(), 'connection': 'not_connected'}, previous['id'] if previous else None)
        event(c, pid, user['user_id'], '配置企业渠道策略', body.name + (' · 启用规划' if body.enabled else ' · 暂不启用'))
        return {'id': rid}


@app.post('/api/projects/{pid}/knowledge')
def add_knowledge(pid: str, body: KnowledgeInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        rid = put(c, pid, 'knowledge', {**body.model_dump(), 'status': 'pending', 'version': 1})
        event(c, pid, user['user_id'], '添加知识资料', body.title)
        return {'id': rid}


class KnowledgeConfirmation(BaseModel):
    version: int = Field(ge=1, strict=True)


class RebuildSource(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1, strict=True)


class KnowledgeRebuild(BaseModel):
    version: int = Field(ge=1, strict=True)
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=80000)
    note: str = Field(min_length=5, max_length=2000)
    sources: list[RebuildSource] = Field(min_length=1, max_length=20)


@app.post('/api/projects/{pid}/knowledge/{rid}/rebuild')
def rebuild_knowledge(pid: str, rid: str, body: KnowledgeRebuild, request: Request):
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor'])
        old = resource(c, pid, rid, 'knowledge')
        if not old.get('derived'):
            raise HTTPException(409, '此入口用于提炼稿重建，原始资料请使用修订功能')
        if old['version'] != body.version:
            raise HTTPException(409, '旧稿已更新，请重新打开重建预览')
        if not body.title.strip() or len(body.note.strip()) < 5 or not body.body.strip():
            raise HTTPException(422, '请填写标题、新正文和具体重建说明')
        if re.sub(r'\s+', '', body.body) == re.sub(r'\s+', '', old['body']):
            raise HTTPException(422, '请根据最新来源重新提炼正文，不能仅刷新来源版本')
        ids = [s.id for s in body.sources]
        if len(set(ids)) != len(ids) or rid in ids:
            raise HTTPException(422, '来源不能重复，也不能引用正在替代的旧稿')
        snapshots = []
        for selected in body.sources:
            doc = resource(c, pid, selected.id, 'knowledge')
            if doc['version'] != selected.version or not knowledge_usable(c, pid, doc):
                raise HTTPException(409, '所选来源已更新或未核准，请重新选择并阅读最新资料')
            snapshots.append({'id': doc['id'], 'title': doc['title'], 'version': doc['version'],
                              'body_sha256': hashlib.sha256(doc['body'].encode('utf-8')).hexdigest()})
        # Identical submissions reuse the pending replacement, never create duplicate drafts.
        key = hashlib.sha256(dump({'old_id': rid, **body.model_dump()}).encode('utf-8')).hexdigest()
        existing = next((d for d in items(c, pid, 'knowledge') if d.get('rebuild_key') == key), None)
        if existing:
            # The request key identifies its original draft, not every future revision.
            # A retry must never imply that an edited/confirmed draft was just saved.
            unchanged = (existing.get('version') == 1 and existing.get('status') == 'pending'
                         and existing.get('derived') is True and not existing.get('knowledge_outdated')
                         and existing.get('title') == body.title.strip()
                         and existing.get('body') == body.body.strip()
                         and existing.get('category') == old['category']
                         and existing.get('rebuild_note') == body.note.strip()
                         and existing.get('source_ids') == ids
                         and existing.get('source_snapshots') == snapshots
                         and existing.get('rebuild_from') == {'id': rid, 'title': old['title'], 'version': old['version']})
            if not unchanged:
                raise HTTPException(409, '重建稿已变化或已核准，请关闭旧表单并刷新，查看现有重建稿；未覆盖或重复创建')
            return {'id': existing['id'], 'created': False}
        new_id = put(c, pid, 'knowledge', {
            'title': body.title.strip(), 'body': body.body.strip(), 'category': old['category'],
            'source': '基于已核准来源重新提炼 · 待客户核准', 'derived': True, 'status': 'pending', 'version': 1,
            'source_ids': ids, 'source_snapshots': snapshots, 'rebuild_key': key,
            'rebuild_from': {'id': rid, 'title': old['title'], 'version': old['version']},
            'rebuild_note': body.note.strip(), 'rebuilt_by': user['identity'], 'rebuilt_at': now(),
        })
        event(c, pid, user['user_id'], '重建提炼稿，等待核准', old['title'] + ' → ' + body.title.strip())
        return {'id': new_id, 'created': True}


@app.post('/api/projects/{pid}/knowledge/{rid}/confirm')
def confirm_knowledge(pid: str, rid: str, body: KnowledgeConfirmation, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'reviewer'])
        item = resource(c, pid, rid, 'knowledge')
        if body.version != item['version']:
            raise HTTPException(409, '资料已更新，请刷新并重新打开资料预览，阅读最新版本后再确认')
        if not knowledge_usable(c, pid, item, require_confirmed=False):
            raise HTTPException(409, '来源版本缺失、已变更或未核准，请核对原始资料并重建问答或提炼稿；旧记录保留追溯')
        if item['status'] == 'confirmed':
            return {'ok': True, 'version': item['version']}
        item['status'] = 'confirmed'
        item.setdefault('confirmation_history', []).append({
            'version': item['version'], 'actor': user['identity'], 'confirmed_at': now(),
            'body_sha256': hashlib.sha256(item['body'].encode('utf-8')).hexdigest(),
        })
        put(c, pid, 'knowledge', item, rid)
        event(c, pid, user['user_id'], '确认知识事实', item['title'] + ' · v' + str(item['version']))
        return {'ok': True, 'version': item['version']}


class SkillInput(BaseModel):
    base_id: str
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=5, max_length=12000)


@app.post('/api/projects/{pid}/skills')
def save_skill(pid: str, body: SkillInput, request: Request):
    base = next((x for x in BASE_SKILLS if x['id'] == body.base_id), None)
    if not base:
        raise HTTPException(422, '基础模板不存在')
    with db() as c:
        user, role = require_prompt_admin(c, request, pid)
        previous = next((x for x in items(c, pid, 'skill') if x['base_id'] == body.base_id), None)
        rid = put(c, pid, 'skill', {**body.model_dump(), 'version': previous['version'] + 1 if previous else 1, 'base_version': base['version']}, previous['id'] if previous else None)
        event(c, pid, user['user_id'], '更新企业专属 Skill', body.name)
        return {'id': rid}


class GenerateInput(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    skill_id: str
    knowledge_ids: list[str] = Field(default_factory=list, max_length=20)
    channels: list[str] = Field(min_length=1, max_length=18)
    keyword: str = Field(default='', max_length=200)
    intent: str = Field(default='', max_length=100)
    customer_question: str = Field(default='', max_length=500)
    prompt_override: str = Field(default='', max_length=12000)
    expert_id: str = 'content'
    auto_knowledge: bool = False
    draft_reference: bool = False


def match_knowledge(c, pid, query, draft_reference=False):
    tokens = re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+', query.lower())
    terms = set(tokens)
    for token in tokens:
        if re.fullmatch(r'[\u4e00-\u9fff]+', token): terms.update(token[i:i+2] for i in range(len(token)-1))
    ranked = []
    for doc in items(c, pid, 'knowledge'):
        if not knowledge_usable(c, pid, doc, require_confirmed=not draft_reference): continue
        title, text = doc['title'].lower(), doc['body'].lower()
        score = sum((4 if t in title else 1) * min(len(t), 8) for t in terms if t in title or t in text)
        if score: ranked.append((score, doc))
    chosen, size = [], 0
    for _, doc in sorted(ranked, key=lambda pair: pair[0], reverse=True):
        if size + len(doc['body']) > 60000: continue
        chosen.append(doc);size += len(doc['body'])
        if len(chosen) == 5: break
    return chosen


def check_channels(channels):
    if not channels or any(x not in CHANNELS for x in channels) or len(set(channels)) != len(channels):
        raise HTTPException(422, '请选择有效且不重复的发布渠道')


def generate_draft(c, pid, body, actor):
    check_channels(body.channels)
    base = next((x for x in BASE_SKILLS if x['id'] == body.skill_id), None)
    if base:
        skill = next((x for x in items(c, pid, 'skill') if x['base_id'] == body.skill_id), base)
    else:
        skill = resource(c, pid, body.skill_id, 'skill')
    docs = (match_knowledge(c, pid, body.keyword+' '+body.customer_question+' '+body.title, body.draft_reference)
            if body.auto_knowledge else [resource(c, pid, x, 'knowledge') for x in dict.fromkeys(body.knowledge_ids)])
    if not docs: raise HTTPException(409, '当前企业未找到匹配且可引用的资料，请调整问题或补充资料')
    if any(not knowledge_usable(c, pid, x, require_confirmed=not body.draft_reference) for x in docs):
        raise HTTPException(409, '请先由审核人确认引用资料')
    name = project(c, pid)['name']
    sources = [{'id': x['id'], 'title': x['title'], 'body': x['body'], 'source': x['source'], 'version': x['version'], 'status':x['status']} for x in docs]
    # No external model is silently invoked: this is an editable, source-backed scaffold.
    sections = ['这份草稿基于已确认的企业资料整理，请补充针对问题的直接回答。', '企业：' + name, '已确认资料\n' + '\n\n'.join('[' + str(i + 1) + '] ' + x['title'] + '\n' + x['body'] for i, x in enumerate(docs)), '采购沟通建议\n请明确应用场景、技术要求、数量、交期与验收方式；涉及性能和认证的表述需附验证条件。', '待补充\n针对该问题的结论、适用边界与企业咨询入口。']
    if skill.get('base_id', skill.get('id')) == 'video':
        sections.append('镜头规划\n01 客户问题｜02 企业产品实拍｜03 应用场景｜04 验证过程｜05 咨询引导。素材与口播待企业确认。')
    brands = items(c, pid, 'brand')
    brand = brands[0] if brands else None
    brand_context = '\n'.join(k + '：' + str(v) for k, v in (brand or {}).items() if k in ['positioning', 'audience', 'pain_points', 'voice', 'preferred', 'forbidden'])
    if body.expert_id not in ['content', 'technical', 'seo_editor', 'video', 'reviewer', 'strategist']:
        raise HTTPException(422, '请选择内容专家')
    content_soul = agent_soul(c, pid, body.expert_id)
    effective_prompt = content_soul['markdown'] + '\n\n本次工作提示词：\n' + (body.prompt_override or skill['prompt']) + ('\n\n企业品牌基因（表达约束，不是事实证据）：\n' + brand_context if brand_context else '')
    if body.customer_question:
        sections.insert(0, '客户问题：' + body.customer_question + '\n用户意图：' + body.intent)
    rid = put(c, pid, 'content', {'title': body.title, 'body': '\n\n'.join(sections), 'status': 'draft', 'revision': 1, 'skill_name': skill['name'], 'skill_version': skill['version'], 'prompt_snapshot': effective_prompt, 'soul_version': content_soul['version'], 'brand_snapshot': brand, 'sources': sources, 'channels': body.channels, 'keyword': body.keyword, 'intent': body.intent, 'customer_question': body.customer_question, 'scheduled': '', 'approved_revision': None, 'review_note': '', 'generator': '本机模板草稿 · 未接入大模型', 'history': []})
    saved = resource(c, pid, rid, 'content')
    saved.update(expert_id=body.expert_id, expert_name=content_soul['name'], draft_reference=body.draft_reference,
                 retrieval={'method':'当前企业关键词匹配' if body.auto_knowledge else '人工选择','source_ids':[x['id'] for x in docs]})
    put(c, pid, 'content', saved, rid)
    event(c, pid, actor, '创建内容草稿', body.title)
    return {'id': rid}


@app.post('/api/projects/{pid}/generate')
def generate(pid: str, body: GenerateInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        return generate_draft(c, pid, body, user['user_id'])

class EditInput(BaseModel):
    revision: int
    title: str = Field(min_length=2, max_length=180)
    body: str = Field(min_length=1, max_length=150000)
    channels: list[str] = Field(max_length=18)
    scheduled: str = Field(default='', max_length=50)


def check_revision(item, revision):
    if item['revision'] != revision:
        raise HTTPException(409, '内容已被其他成员修改，请刷新后重新预览')


@app.put('/api/projects/{pid}/contents/{rid}')
def edit_content(pid: str, rid: str, body: EditInput, request: Request):
    # Editorial drafts may be channel-neutral; approval and publish still require channels.
    if body.channels:
        check_channels(body.channels)
    if body.scheduled:
        try:
            datetime.fromisoformat(body.scheduled)
        except ValueError:
            raise HTTPException(422, '排期时间格式错误')
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        item = resource(c, pid, rid, 'content')
        check_revision(item, body.revision)
        if item['status'] == 'generating' or any(j['status'] == 'running' and j['job_type'].startswith('wp_') and j['payload'].get('content_id') == rid for j in items(c, pid, 'execution')):
            raise HTTPException(409, '内容正在生成或提交平台，请等待任务结束')
        item.pop('quality', None)
        # Channel variants must be regenerated/reviewed after master copy changes.
        item.pop('platform_payloads', None)
        if item.get('generation_error') and body.body.strip() != item['body'].strip():
            item['generation_error'] = False
            item['generator'] = '人工完善 · 原模型执行未成功'
        item['history'].append({k: item[k] for k in ['revision', 'title', 'body', 'channels', 'status']})
        if item.get('layout') and (body.title != item['title'] or body.body != item['body']):
            item['layout']['outdated'] = True
        item.update(body.model_dump())
        item.update(revision=body.revision + 1, status='draft', approved_revision=None, review_note='')
        put(c, pid, 'content', item, rid)
        for pub in items(c, pid, 'publication'):
            if pub['content_id'] == rid and pub['status'] in ('awaiting_connector', 'wp_draft'):
                pub['status'] = 'cancelled'
                put(c, pid, 'publication', pub, pub['id'])
        event(c, pid, user['user_id'], '修改内容，重新审核', item['title'] + ' · v' + str(item['revision']))
        return {'ok': True}


class ReviewInput(BaseModel):
    revision: int
    action: str
    note: str = Field(default='', max_length=3000)


@app.post('/api/projects/{pid}/contents/{rid}/review')
def review(pid: str, rid: str, body: ReviewInput, request: Request):
    roles = ['owner', 'editor'] if body.action == 'submit' else ['owner', 'reviewer']
    with db() as c:
        user, role = scope(c, request, pid, roles)
        item = resource(c, pid, rid, 'content')
        check_revision(item, body.revision)
        if body.action == 'approve' and not item.get('channels'):
            raise HTTPException(409, '请先选择发布渠道并预览对应版本，再批准发送')
        if body.action in ('submit', 'approve'):
            sample_review.require_current_layout(item)
            require_content_provenance(c, pid, item)
            if item.get('generation_error'):
                raise HTTPException(409, '模型生成未成功，请重新生成或人工完善正文后再提交审核')
            for source in item['sources']:
                latest = resource(c, pid, source['id'], 'knowledge')
                if not knowledge_usable(c, pid, latest) or latest['version'] != source['version']:
                    raise HTTPException(409, '引用知识已变更或未核准，请依据最新知识重新创作')
        if body.action == 'submit' and item['status'] in ('draft', 'rejected'):
            item['status'] = 'pending'
        elif body.action == 'approve' and item['status'] == 'pending':
            item.update(status='approved', approved_revision=item['revision'], approved_by=user['identity'], approved_at=now())
        elif body.action == 'reject' and item['status'] == 'pending' and body.note.strip():
            item.update(status='rejected', approved_revision=None)
        else:
            raise HTTPException(409, '状态不允许此操作；退回时需填写修改意见')
        item['review_note'] = body.note
        put(c, pid, 'content', item, rid)
        event(c, pid, user['user_id'], {'submit': '提交客户审核', 'approve': '审核通过', 'reject': '退回修改'}[body.action], item['title'] + ' · v' + str(item['revision']) + (' · ' + body.note if body.note else ''))
        return {'ok': True}


class RevisionInput(BaseModel):
    revision: int


@app.post('/api/projects/{pid}/contents/{rid}/publish')
def publish(pid: str, rid: str, body: RevisionInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        item = resource(c, pid, rid, 'content')
        check_revision(item, body.revision)
        sample_review.require_current_layout(item)
        require_content_provenance(c, pid, item)
        if item['status'] != 'approved' or item['approved_revision'] != item['revision']:
            raise HTTPException(409, '仅可交付已审核通过的当前版本')
        if not item.get('channels'):
            raise HTTPException(409, '尚未选择发布渠道')
        for snapshot in item['sources']:
            source = resource(c, pid, snapshot['id'], 'knowledge')
            if source['version'] != snapshot['version'] or not knowledge_usable(c, pid, source):
                raise HTTPException(409, '内容引用的问答或知识已失效，请重新创作并审核')
        existing = items(c, pid, 'publication')
        created = []
        for channel in item['channels']:
            if any(x['content_id'] == rid and x['revision'] == item['revision'] and x['channel'] == channel for x in existing):
                continue
            payload = delivery_runtime.payload_for(item, channel)
            created.append(put(c, pid, 'publication', {'content_id': rid, 'revision': item['revision'], 'title': payload['title'], 'body_snapshot': payload['body'], 'cover_id': payload.get('cover_id', ''), 'attachment_ids': payload.get('attachment_ids', []), 'cta_url': payload.get('cta_url', ''), 'channel': channel, 'scheduled': item['scheduled'], 'status': 'awaiting_connector', 'url': '', 'method': 'manual', 'approved_by': item.get('approved_by', ''), 'approved_at': item.get('approved_at', '')}))
        if created:
            event(c, pid, user['user_id'], '创建发布交付任务', item['title'] + ' · ' + str(len(created)) + ' 个渠道；待接入或人工交付')
        return {'ids': created, 'external_sent': False}


class ReceiptInput(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


@app.post('/api/projects/{pid}/publications/{rid}/receipt')
def receipt(pid: str, rid: str, body: ReceiptInput, request: Request):
    url = check_url(body.url)
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        item = resource(c, pid, rid, 'publication')
        if item['status'] != 'awaiting_connector':
            raise HTTPException(409, '该任务已登记或已取消')
        content = resource(c, pid, item['content_id'], 'content')
        if content['revision'] != item['revision'] or item['channel'] not in content.get('channels', []):
            raise HTTPException(409, '交付版本或渠道已变更，不能登记为当前有效交付；请核对旧文并重新审核')
        approval = content_approval_summary(c, pid, content)
        if not approval['effective_approved']:
            raise HTTPException(409, '内容审批或知识来源已失效，不能登记为当前有效交付：' + '；'.join(approval['reasons']))
        platform_jobs = [j for j in items(c, pid, 'execution')
                         if j['job_type'].startswith('wp_') and j['payload'].get('resource_id') == rid]
        if any(j['status'] in ('running', 'unknown') for j in platform_jobs):
            raise HTTPException(409, '平台任务正在执行或结果未知，请先在执行记录核对回执，再登记人工发布')
        # BEGIN IMMEDIATE serializes this handoff with the worker claiming a job.
        # Once a manual receipt exists, no queued automatic submission may survive it.
        for job in platform_jobs:
            if job['status'] == 'queued':
                job.update(status='cancelled', stage='人工回执已登记，取消排队提交', finished_at=now(),
                           result={'reason': 'manual_receipt', 'publication_id': rid}, error='')
                put(c, pid, 'execution', job, job['id'])
                event(c, pid, user['user_id'], '人工回执取消排队任务', job['job_type'] + ' · ' + rid)
        item.update(status='recorded', url=url, received_at=now(), method='manual', recorded_by=user['identity'])
        put(c, pid, 'publication', item, rid)
        event(c, pid, user['user_id'], '登记人工发布回执', item['channel'] + ' · ' + item['title'])
        return {'ok': True}


class SampleInput(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    platform: str
    answer: str = Field(min_length=2, max_length=15000)
    mentioned: bool
    recommended: bool | None = None
    citation: str = Field(default='', max_length=2000)
    observed_at: str


@app.post('/api/projects/{pid}/diagnosis/samples')
def add_sample(pid: str, body: SampleInput, request: Request):
    if body.platform not in PLATFORMS:
        raise HTTPException(422, '不支持的平台')
    try:
        stamp = datetime.fromisoformat(body.observed_at)
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, '请提供包含时区且不晚于当前时间的采样时间')
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        reports = items(c, pid, 'diagnosis')
        report = next((x for x in reports if x['status'] != 'sample'), {'samples': []})
        report['samples'].append({**body.model_dump(), 'citation': check_url(body.citation), 'source': 'manual'})
        report.update(status='manual', summary='人工录入的抽样观察；未自动验证平台回答，结果只代表当前问题与采样时间。')
        put(c, pid, 'diagnosis', report, report.get('id'))
        event(c, pid, user['user_id'], '补充 GEO 诊断证据', body.platform + ' · ' + body.question)
        return {'ok': True}


class LeadInput(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=1, max_length=200)
    source: str = Field(default='未知', max_length=200)
    need: str = Field(min_length=1, max_length=3000)
    content_id: str = ''
    contact_method: str = Field(default='其他', max_length=50)
    origin_url: str = Field(default='', max_length=2000)
    wecom_entry_id: str = ''


@app.post('/api/projects/{pid}/leads')
def add_lead(pid: str, body: LeadInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        if body.content_id:
            resource(c, pid, body.content_id, 'content')
        if body.wecom_entry_id:
            resource(c, pid, body.wecom_entry_id, 'contact_entry')
        rid = put(c, pid, 'lead', {**body.model_dump(), 'origin_url': check_url(body.origin_url), 'status': 'new', 'owner': '待分配', 'note': '', 'next_followup': '', 'revision': 1, 'history': []})
        event(c, pid, user['user_id'], '录入客资', body.company)
        return {'id': rid}


class LeadUpdate(BaseModel):
    status: str
    owner: str = Field(max_length=100)
    note: str = Field(max_length=5000)
    next_followup: str = ''
    revision: int | None = None


@app.put('/api/projects/{pid}/leads/{rid}')
def update_lead(pid: str, rid: str, body: LeadUpdate, request: Request):
    if body.status not in ['new', 'contacted', 'qualified', 'won', 'invalid']:
        raise HTTPException(422, '无效的跟进状态')
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        item = resource(c, pid, rid, 'lead')
        if body.revision is not None and item.get('revision', 1) != body.revision:
            raise HTTPException(409, '线索已更新，请刷新后重试')
        if body.next_followup:
            try:
                stamp = datetime.fromisoformat(body.next_followup)
                if stamp.tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, '下次跟进时间需要有效日期和时区')
        item.setdefault('history', []).append({'status': body.status, 'owner': body.owner, 'note': body.note, 'at': now(), 'actor': user['identity'], 'next_followup': body.next_followup})
        revision = item.get('revision', 1)
        item.update(body.model_dump())
        item['revision'] = revision + 1
        put(c, pid, 'lead', item, rid)
        event(c, pid, user['user_id'], '更新客资跟进', item['company'] + ' · ' + body.status)
        return {'ok': True}


class MemberInput(BaseModel):
    identity: str
    role: str


@app.post('/api/projects/{pid}/members')
def add_member(pid: str, body: MemberInput, request: Request):
    if body.role not in ['editor', 'reviewer', 'viewer']:
        raise HTTPException(422, '请选择编辑、审核人或只读成员')
    with db() as c:
        user, role = scope(c, request, pid, ['owner'])
        target = c.execute('SELECT id FROM users WHERE identity=?', (identity_value(body.identity),)).fetchone()
        if not target:
            raise HTTPException(404, '该成员需先在本机应用注册账号')
        previous = c.execute('SELECT role FROM members WHERE project_id=? AND user_id=?', (pid, target['id'])).fetchone()
        if previous and previous['role'] == 'owner':
            raise HTTPException(409, '不能修改空间所有者')
        c.execute('INSERT INTO members VALUES(?,?,?) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role', (pid, target['id'], body.role))
        event(c, pid, user['user_id'], '设置空间成员', body.identity + ' · ' + body.role)
        return {'ok': True}


@app.get('/api/projects/{pid}/export')
def export(pid: str, request: Request):
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor', 'reviewer'])
        payload = {'project': project(c, pid), 'exported_at': now(), 'stats': stats(c, pid), 'records': {kind: items(c, pid, kind) for kind in ['content', 'publication', 'diagnosis', 'lead', 'execution', 'observation', 'geo_snapshot', 'seo_audit', 'media_opportunity']}, 'events': [dict(r) for r in c.execute('SELECT * FROM events WHERE project_id=? ORDER BY created', (pid,))]}
        return Response(dump(public_records(payload, user)), media_type='application/json', headers={'Content-Disposition': 'attachment; filename="geo-delivery.json"'})


class InsightInput(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    platform: str = Field(min_length=1, max_length=100)
    url: str = Field(default='', max_length=2000)
    question: str = Field(min_length=2, max_length=3000)
    keyword: str = Field(default='', max_length=200)
    opportunity: str = Field(default='', max_length=1500)


class UserIntentEdit(BaseModel):
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    tag: str = Field(default='', max_length=200)
    question: str = Field(default='', max_length=3000)
    strategy: str = Field(default='', max_length=5000)
    cta: str = Field(default='', max_length=1500)


@app.put('/api/projects/{pid}/user-intents/{rid}')
def edit_user_intent(pid: str, rid: str, body: UserIntentEdit, request: Request):
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor'])
        current = resource(c, pid, rid, 'user_intent')
        if current['version'] != body.version:
            raise HTTPException(409, '该意图已更新，请重新打开后修改')
        if not body.title.strip(): raise HTTPException(422, '请填写标题')
        history = current.get('history', []) + [{k: v for k, v in current.items() if k != 'history'}]
        current.update(body.model_dump(exclude={'version'}), version=body.version + 1, history=history)
        put(c, pid, 'user_intent', current, rid)
        event(c, pid, user['user_id'], '修改用户意图', current['title'])
        return {'id': rid, 'version': current['version']}


@app.post('/api/projects/{pid}/insights')
def save_insight(pid: str, body: InsightInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        rid = put(c, pid, 'insight', {**body.model_dump(), 'url': check_url(body.url), 'source': 'manual'})
        event(c, pid, user['user_id'], '记录客户问题与社区洞察', body.title)
        return {'id': rid}


class BrandInput(BaseModel):
    company_intro: str = Field(default='', max_length=12000)
    positioning: str = Field(default='', max_length=3000)
    audience: str = Field(default='', max_length=3000)
    pain_points: str = Field(default='', max_length=3000)
    voice: str = Field(default='', max_length=3000)
    preferred: str = Field(default='', max_length=3000)
    forbidden: str = Field(default='', max_length=3000)


@app.post('/api/projects/{pid}/brand')
def save_brand(pid: str, body: BrandInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        old = items(c, pid, 'brand')
        version = old[0]['version'] + 1 if old else 1
        previous = old[0] if old else {}
        history = previous.get('history', []) + ([{'version':previous['version'], 'at':now(), 'fields':{k:previous.get(k,'') for k in BrandInput.model_fields}}] if old else [])
        rid = put(c, pid, 'brand', {**previous, **body.model_dump(), 'version': version, 'history':history}, old[0]['id'] if old else None)
        event(c, pid, user['user_id'], '更新品牌基因', 'v' + str(version) + ' · 后续内容自动保存表达约束快照')
        return {'id': rid}


class BrandSectionInput(BaseModel):
    value: str = Field(max_length=12000)
    version: int = Field(ge=0)


@app.put('/api/projects/{pid}/brand/overview')
def save_brand_overview(pid: str, body: BrandSectionInput, request: Request):
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor'])
        brand = next(iter(items(c, pid, 'brand')), {})
        doc = resource(c, pid, brand.get('overview_knowledge_id', ''), 'knowledge')
        if doc['version'] != body.version: raise HTTPException(409, '概述已更新，请刷新后重新编辑')
        if not body.value.strip(): raise HTTPException(422, '综合概述不能为空')
        history = doc.get('history', []) + [{k: v for k, v in doc.items() if k != 'history'}]
        doc.update(body=body.value, version=doc['version'] + 1, status='pending', history=history)
        for key in ('confirmed_at', 'confirmed_by'): doc.pop(key, None)
        put(c, pid, 'knowledge', doc, doc['id'])
        event(c, pid, user['user_id'], '更新品牌整体概述', '知识版本 v' + str(doc['version']) + ' · 待核准')
        return {'id': doc['id'], 'version': doc['version']}


@app.put('/api/projects/{pid}/brand/sections/{section}')
def save_brand_section(pid: str, section: str, body: BrandSectionInput, request: Request):
    if section not in BrandInput.model_fields: raise HTTPException(422, '无效的品牌栏目')
    if section != 'company_intro' and len(body.value) > 3000: raise HTTPException(422, '此栏目最多 3000 字')
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor'])
        old = next(iter(items(c, pid, 'brand')), {'version':0})
        if old['version'] != body.version: raise HTTPException(409, '品牌档案已更新，请重新打开栏目后保存；当前输入已保留')
        history=old.get('history', []) + [{'version':old['version'], 'at':now(), 'section':section, 'actor':user['identity'], 'fields':{k:old.get(k,'') for k in BrandInput.model_fields}}]
        rid=put(c,pid,'brand',{**old,section:body.value,'version':old['version']+1,'history':history},old.get('id'))
        event(c,pid,user['user_id'],'更新品牌独立栏目',section+' · v'+str(old['version']+1))
        return {'id':rid,'version':old['version']+1}


class FaqInput(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    answer: str = Field(min_length=2, max_length=15000)
    category: str = Field(default='产品问答', max_length=50)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    source_versions: dict[str, int] = Field(default_factory=dict)
    draft_reference: bool = False
    origin_kind: str = Field(default='', max_length=30)
    origin_id: str = Field(default='', max_length=100)


@app.post('/api/projects/{pid}/faq')
def save_faq(pid: str, body: FaqInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        if not body.question.strip() or not body.answer.strip():
            raise HTTPException(422, '请填写问题和答案')
        if body.origin_kind or body.origin_id:
            if body.origin_kind not in ('insight', 'user_intent') or not body.origin_id:
                raise HTTPException(422, '问题来源无效')
            resource(c, pid, body.origin_id, body.origin_kind)
        sources = [resource(c, pid, r, 'knowledge') for r in body.source_ids]
        if any(not knowledge_usable(c, pid, s, require_confirmed=not body.draft_reference) for s in sources):
            raise HTTPException(409, '请先核准问答引用资料，并使用当前有效版本')
        if body.source_versions and (set(body.source_versions) != set(body.source_ids) or any(body.source_versions.get(s['id']) != s['version'] for s in sources)):
            raise HTTPException(409, '引用资料已更新，请重新查询并核对后保存')
        kid = put(c, pid, 'knowledge', {'title': body.question, 'body': body.answer, 'category': 'FAQ', 'source': '人工编写百问百答' + ('；依据：' + '、'.join(s['title'] for s in sources) if sources else '；待补充事实依据'), 'status': 'pending', 'version': 1})
        rid = put(c, pid, 'faq', {**body.model_dump(), 'knowledge_id': kid, 'source_snapshots': [{'id': s['id'], 'title': s['title'], 'version': s['version']} for s in sources]})
        event(c, pid, user['user_id'], '保存百问百答', body.question)
        return {'id': rid}


class FaqEdit(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    answer: str = Field(min_length=2, max_length=15000)
    category: str = Field(min_length=1, max_length=50)
    version: int = Field(ge=1, strict=True)


@app.put('/api/projects/{pid}/faq/{rid}')
def edit_faq(pid: str, rid: str, body: FaqEdit, request: Request):
    with db() as c:
        user, _ = scope(c, request, pid, ['owner', 'editor'])
        faq = resource(c, pid, rid, 'faq')
        doc = resource(c, pid, faq['knowledge_id'], 'knowledge')
        if doc['version'] != body.version:
            raise HTTPException(409, '答案已更新，请重新打开后核对；当前输入尚未保存')
        if not all(s.strip() for s in (body.question, body.answer, body.category)):
            raise HTTPException(422, '请填写问题、分类和答案')
        doc['history'] = doc.get('history', []) + [{k: v for k, v in doc.items() if k != 'history'}]
        faq['history'] = faq.get('history', []) + [{k: v for k, v in faq.items() if k != 'history'}]
        doc.update(title=body.question.strip(), body=body.answer.strip(), version=doc['version']+1, status='pending')
        for key in ('confirmed_at', 'confirmed_by'): doc.pop(key, None)
        faq.update(question=doc['title'], answer=doc['body'], category=body.category.strip())
        # Keep original provenance; editing an answer must not silently rebase its sources.
        put(c, pid, 'knowledge', doc, doc['id'])
        put(c, pid, 'faq', faq, rid)
        event(c, pid, user['user_id'], '修改企业问答', doc['title'] + ' · v' + str(doc['version']))
        return {'id': rid, 'version': doc['version']}


class QueryInput(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    include_pending: bool = False


@app.post('/api/projects/{pid}/knowledge-search')
def knowledge_search(pid: str, body: QueryInput, request: Request):
    with db() as c:
        scope(c, request, pid)
        query = body.query.strip().lower()
        if not query: raise HTTPException(422, '请输入问题或关键词')
        tokens = re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+', query)
        grams = set(tokens)
        for token in tokens:
            if re.fullmatch(r'[\u4e00-\u9fff]+', token):
                grams.update(token[i:i+2] for i in range(len(token)-1))
        ranked = []
        for doc in items(c, pid, 'knowledge'):
            if not knowledge_usable(c, pid, doc, require_confirmed=not body.include_pending):
                continue
            text = (doc['title'] + '\n' + doc['body']).lower()
            score = (20 if query in text else 0) + sum(len(t) for t in grams if t in text)
            if score:
                pos = text.find(query)
                if pos < 0:
                    pos = min((text.find(t) for t in grams if t in text), default=0)
                ranked.append({'id': doc['id'], 'title': doc['title'], 'excerpt': (doc['title'] + '\n' + doc['body'])[max(0,pos-60):pos+800], 'source': doc['source'], 'version': doc['version'], 'status': doc['status'], 'score': score})
        ranked.sort(key=lambda x: x['score'], reverse=True)
        return {'mode': '关键词资料检索 · 原文摘录，不是模型生成答案', 'matches': ranked[:8]}


@app.post('/api/projects/{pid}/assets')
async def upload_asset(pid: str, request: Request, filename: str):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        actor = user['user_id']
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 20 * 1024 * 1024:
            raise HTTPException(413, '单个文件上限 20 MB')
        chunks.append(chunk)
    raw = b''.join(chunks)
    ext = Path(filename).suffix.lower()
    allowed = {'.png': ('image/png', '图片'), '.jpg': ('image/jpeg', '图片'), '.jpeg': ('image/jpeg', '图片'), '.webp': ('image/webp', '图片'), '.pdf': ('application/pdf', '资料'), '.mp4': ('video/mp4', '视频')}
    if ext not in allowed or not raw:
        raise HTTPException(422, '支持 PNG、JPG、WebP、PDF 和 MP4，单个不超过 20 MB')
    valid = (ext=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ['.jpg','.jpeg'] and raw.startswith(b'\xff\xd8\xff')) or (ext=='.webp' and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP') or (ext=='.pdf' and raw.startswith(b'%PDF-')) or (ext=='.mp4' and raw[4:8]==b'ftyp')
    if not valid:
        raise HTTPException(422, '文件内容与扩展名不匹配')
    if len(filename)>200:
        raise HTTPException(422, '文件名过长')
    with db() as c:
        scope(c, request, pid, ['owner', 'editor'])
        rid = uid()
        folder = DB_PATH.parent / 'assets' / pid
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (rid+ext)
        path.write_bytes(raw)
        try:
            saved = put(c, pid, 'asset', {'title': Path(filename).name, 'category': allowed[ext][1], 'mime': allowed[ext][0], 'size': size, 'storage_key': rid+ext})
            event(c, pid, actor, '归档企业素材', Path(filename).name)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {'id': saved}


@app.get('/api/projects/{pid}/assets/{rid}/file')
def asset_file(pid: str, rid: str, request: Request):
    with db() as c:
        scope(c, request, pid)
        item = resource(c, pid, rid, 'asset')
        path = DB_PATH.parent / 'assets' / pid / item['storage_key']
        return FileResponse(path, media_type=item['mime'], filename=item['title'], content_disposition_type='inline' if item['category'] in ['图片','视频'] else 'attachment', headers={'Cache-Control': 'no-store'})


class AutomationInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    task_type: str
    start_at: str
    frequency: str
    title: str = Field(default='', max_length=180)
    skill_id: str = 'faq'
    knowledge_ids: list[str] = Field(default_factory=list, max_length=20)
    channels: list[str] = Field(default_factory=list, max_length=18)
    submit_review: bool = True
    note: str = Field(default='', max_length=2000)
    keyword: str = Field(default='', max_length=200)
    intent: str = Field(default='', max_length=100)
    customer_question: str = Field(default='', max_length=500)
    prompt_override: str = Field(default='', max_length=12000)
    expert_id: str = 'content'


def validate_automation(c, pid, body):
    if body.task_type not in ['content', 'reminder'] or body.frequency not in ['once', 'daily', 'weekly']:
        raise HTTPException(422, '请选择有效的任务类型与频率')
    try:
        stamp = datetime.fromisoformat(body.start_at)
        if stamp.tzinfo is None or stamp <= datetime.now(timezone.utc):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, '首次执行时间必须晚于当前时间，并包含时区')
    if body.task_type == 'content':
        if len(body.title.strip()) < 2 or not body.knowledge_ids:
            raise HTTPException(422, '请填写内容主题并选择已确认资料')
        check_channels(body.channels)
        if body.skill_id not in [s['id'] for s in BASE_SKILLS]:
            resource(c, pid, body.skill_id, 'skill')
        for rid in body.knowledge_ids:
            if resource(c, pid, rid, 'knowledge')['status'] != 'confirmed':
                raise HTTPException(409, '自动创作只可引用已确认的企业资料')
    return stamp.isoformat(timespec='seconds')


@app.post('/api/projects/{pid}/automations')
def create_automation(pid: str, body: AutomationInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        start_at = validate_automation(c, pid, body)
        rid = put(c, pid, 'automation', {**body.model_dump(), 'start_at': start_at, 'next_run': start_at, 'status': 'active', 'owner_id': user['user_id'], 'last_run': '', 'last_error': '', 'run_count': 0})
        event(c, pid, user['user_id'], '创建自动化任务', body.name + ' · ' + body.frequency)
        return {'id': rid}


def next_occurrence(task, after):
    """Fixed-offset daily/weekly cadence; skip missed slots, do not flood after restart."""
    if task['frequency'] == 'once':
        return None
    due = datetime.fromisoformat(task['next_run'])
    interval = timedelta(days=1 if task['frequency'] == 'daily' else 7)
    steps = max(1, int((after - due) // interval) + 1)
    return (due + steps * interval).isoformat(timespec='seconds')


def run_automation(c, pid, task, actor, trigger='scheduled', at=None):
    stamp = at or datetime.now(timezone.utc)
    # The enclosing immediate transaction serializes execution and cursor updates.
    member = c.execute('SELECT role FROM members WHERE project_id=? AND user_id=?', (pid, task['owner_id'])).fetchone()
    if not member or member['role'] not in ('owner', 'editor'):
        raise HTTPException(403, '任务创建者已失去编辑权限，请暂停任务并重新配置负责人')
    result_id = ''
    if task['task_type'] == 'content':
        body = GenerateInput(title=task['title'], skill_id=task['skill_id'], knowledge_ids=task['knowledge_ids'], channels=task['channels'], expert_id=task.get('expert_id', 'content'), **{k: task.get(k, '') for k in ['keyword', 'intent', 'customer_question', 'prompt_override']})
        result_id = generate_draft(c, pid, body, actor)['id']
        content = resource(c, pid, result_id, 'content')
        content.update(automation_id=task['id'], scheduled=stamp.isoformat(timespec='seconds'), status='pending' if task['submit_review'] else 'draft')
        put(c, pid, 'content', content, result_id)
    put(c, pid, 'automation_run', {'automation_id': task['id'], 'name': task['name'], 'task_type': task['task_type'], 'trigger': trigger, 'status': 'success', 'content_id': result_id, 'scheduled_for': task['next_run'], 'executed_at': stamp.isoformat(timespec='seconds'), 'message': ('模板草稿已生成，等待客户审核' if task['submit_review'] else '模板草稿已保存') if result_id else (task['note'] or '请处理内容发布与复盘任务')})
    task.update(last_run=stamp.isoformat(timespec='seconds'), run_count=task['run_count'] + 1, last_error='')
    if trigger == 'scheduled':
        next_run = next_occurrence(task, stamp)
        task.update(next_run=next_run or '', status='active' if next_run else 'completed')
    put(c, pid, 'automation', task, task['id'])
    event(c, pid, actor, '自动化执行完成' if result_id else '排期提醒已到期', task['name'] + ' · ' + ('已生成待处理内容' if result_id else task['note']))
    return {'content_id': result_id, 'external_sent': False}


class AutomationAction(BaseModel):
    action: str


@app.post('/api/projects/{pid}/automations/{rid}/action')
def automation_action(pid: str, rid: str, body: AutomationAction, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner', 'editor'])
        task = resource(c, pid, rid, 'automation')
        if body.action == 'pause' and task['status'] == 'active':
            task['status'] = 'paused'
        elif body.action == 'resume' and task['status'] in ('paused', 'failed'):
            if datetime.fromisoformat(task['next_run']) <= datetime.now(timezone.utc):
                task['next_run'] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(timespec='seconds') if task['frequency'] == 'once' else next_occurrence(task, datetime.now(timezone.utc))
            task.update(status='active', last_error='')
        elif body.action == 'run' and task['status'] in ('active', 'paused'):
            # Deliberate manual run leaves the planned next occurrence intact.
            if task['last_run'] and (datetime.now(timezone.utc)-datetime.fromisoformat(task['last_run'])).total_seconds() < 15:
                raise HTTPException(409, '刚刚已执行，请稍后再试')
            return run_automation(c, pid, task, user['user_id'], 'manual')
        else:
            raise HTTPException(409, '当前状态不支持该操作')
        put(c, pid, 'automation', task, rid)
        event(c, pid, user['user_id'], '调整自动化状态', task['name'] + ' · ' + task['status'])
        return {'ok': True}


def scheduler_tick(at=None):
    stamp = at or datetime.now(timezone.utc)
    with db() as c:
        tasks = c.execute("SELECT id,project_id FROM resources WHERE kind='automation'").fetchall()
        for row in tasks:
            pid = row['project_id']
            task = resource(c, pid, row['id'], 'automation')
            if task['status'] != 'active' or datetime.fromisoformat(task['next_run']) > stamp:
                continue
            c.execute('SAVEPOINT automation_attempt')
            try:
                run_automation(c, pid, task, task['owner_id'], at=stamp)
                c.execute('RELEASE automation_attempt')
            except Exception as exc:
                c.execute('ROLLBACK TO automation_attempt')
                c.execute('RELEASE automation_attempt')
                reason = str(exc.detail) if isinstance(exc, HTTPException) else '执行异常，请检查服务日志'
                if not isinstance(exc, HTTPException):
                    logging.exception('Automation failed: %s', row['id'])
                task = resource(c, pid, row['id'], 'automation')
                task.update(status='failed', last_error=reason)
                put(c, pid, 'automation', task, task['id'])
                put(c, pid, 'automation_run', {'automation_id': task['id'], 'name': task['name'], 'task_type': task['task_type'], 'trigger': 'scheduled', 'status': 'failed', 'content_id': '', 'scheduled_for': task['next_run'], 'executed_at': stamp.isoformat(timespec='seconds'), 'message': reason})
                event(c, pid, task['owner_id'], '自动化执行失败并暂停', task['name'] + ' · ' + reason)


scheduler_stop = threading.Event()
scheduler_thread = None


def scheduler_loop():
    while not scheduler_stop.is_set():
        try:
            scheduler_tick()
        except Exception:
            logging.exception('Scheduler tick failed')
        scheduler_stop.wait(15)


@app.on_event('startup')
def start_scheduler():
    global scheduler_thread
    scheduler_stop.clear()
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True, name='geo-local-scheduler')
    scheduler_thread.start()


@app.on_event('shutdown')
def stop_scheduler():
    scheduler_stop.set()
    if scheduler_thread:
        scheduler_thread.join(timeout=20)


class ContactEntryInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    method: str = Field(max_length=50)
    value: str = Field(min_length=1, max_length=200)
    url: str = Field(default='', max_length=2000)
    placement: str = Field(default='', max_length=1000)
    owner: str = Field(default='', max_length=120)
    note: str = Field(default='', max_length=2000)


@app.post('/api/projects/{pid}/contact-entries')
def add_contact_entry(pid: str, body: ContactEntryInput, request: Request):
    if body.method not in ['企业微信', '电话', '邮箱', '官网表单', '其他']:
        raise HTTPException(422, '无效的联系入口类型')
    with db() as c:
        user, role = scope(c, request, pid, ['owner','editor'])
        rid = put(c, pid, 'contact_entry', {**body.model_dump(), 'url':check_url(body.url), 'connection':'manual'})
        event(c, pid, user['user_id'], '配置线上联系入口', body.name)
        return {'id':rid}


class CommentInput(BaseModel):
    platform: str = Field(min_length=1, max_length=100)
    author: str = Field(default='未提供', max_length=200)
    text: str = Field(min_length=2, max_length=5000)
    source_url: str = Field(default='', max_length=2000)
    external_id: str = Field(default='', max_length=200)
    contact: str = Field(default='', max_length=200)


class CommentBatch(BaseModel):
    comments: list[CommentInput] = Field(min_length=1, max_length=100)


@app.post('/api/projects/{pid}/comments/import')
def import_comments(pid: str, body: CommentBatch, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner','editor'])
        known = {x['fingerprint'] for x in items(c,pid,'comment')}
        ids, skipped = [], 0
        for entry in body.comments:
            data = entry.model_dump()
            data['source_url'] = check_url(entry.source_url)
            key = [entry.platform, entry.external_id] if entry.external_id else [entry.platform,data['source_url'],entry.author,entry.text.strip()]
            fingerprint = hashlib.sha256(dump(key).encode()).hexdigest()
            if fingerprint in known:
                skipped += 1
                continue
            known.add(fingerprint)
            ids.append(put(c,pid,'comment',{**data,'fingerprint':fingerprint,'capture_method':'manual_import','status':'new','lead_id':''}))
        if ids:
            event(c,pid,user['user_id'],'导入评论 / 咨询',str(len(ids))+' 条；重复跳过 '+str(skipped)+' 条')
        return {'ids':ids,'skipped':skipped}


class CommentAction(BaseModel):
    action: str


@app.post('/api/projects/{pid}/comments/{rid}/action')
def comment_action(pid: str, rid: str, body: CommentAction, request: Request):
    with db() as c:
        user, role = scope(c,request,pid,['owner','editor'])
        item = resource(c,pid,rid,'comment')
        if body.action == 'convert':
            if item['lead_id']:
                return {'lead_id':item['lead_id']}
            lead_id = put(c,pid,'lead',{'company':item['author'] or '评论咨询者','contact':item['contact'] or '未留联系方式，待人工确认','source':item['platform']+' · 评论导入','need':item['text'],'status':'new','owner':'待分配','note':'评论转入，尚未确认有效性','content_id':'','comment_id':rid,'origin_url':item['source_url'],'contact_method':'评论咨询','wecom_entry_id':'','next_followup':'','revision':1,'history':[]})
            item.update(lead_id=lead_id,status='converted')
            put(c,pid,'comment',item,rid)
            event(c,pid,user['user_id'],'评论转为待核实线索',item['platform']+' · '+item['author'])
            return {'lead_id':lead_id}
        if body.action not in ['ignore','restore'] or item['lead_id']:
            raise HTTPException(409,'当前评论状态不支持此操作')
        item['status'] = 'ignored' if body.action=='ignore' else 'new'
        put(c,pid,'comment',item,rid)
        event(c,pid,user['user_id'],'更新评论状态',item['platform']+' · '+item['status'])
        return {'ok':True}


AGENT_ROLES = {
    'strategist': {'name': '策略胡老师', 'module': 'content', 'job': 'AI 内容策略、问题簇与证据规划'},
    'director': {'name': '铸匠 · 项目主管', 'module': 'workspace', 'job': '统筹需求、任务与进度'},
    'knowledge': {'name': '知识管家', 'module': 'knowledge', 'job': '资料、品牌表达与问答'},
    'content': {'name': '内容策划', 'module': 'content', 'job': '客户意图、内容与审核'},
    'diagnosis': {'name': '诊断分析师', 'module': 'diagnosis', 'job': 'GEO 证据与优化建议'},
    'publishing': {'name': '发布管家', 'module': 'publish', 'job': '渠道排期与发布交付'},
    'leads': {'name': '客资助理', 'module': 'leads', 'job': '咨询跟进与需求反馈'},
    'technical': {'name': '技术写作专家', 'module': 'content', 'job': '产品参数、工况与技术指南'},
    'seo_editor': {'name': 'SEO / GEO 编辑', 'module': 'content', 'job': '问题意图、结构与可引用内容'},
    'video': {'name': '视频脚本专家', 'module': 'content', 'job': '镜头、口播与素材规划'},
    'reviewer': {'name': '内容审校专家', 'module': 'content', 'job': '事实、表达与待核实建议'},
}


def agent_soul(c, pid, agent_id):
    if agent_id not in AGENT_ROLES:
        raise HTTPException(404, '智能体不存在')
    custom = next((x for x in items(c, pid, 'soul') if x['agent_id'] == agent_id), None)
    md = custom['markdown'] if custom else (ROOT / 'agents' / agent_id / 'soul.md').read_text(encoding='utf-8')
    if agent_id in ('content','technical','seo_editor','video','reviewer','strategist'):
        shared_rules = (ROOT / 'agents' / 'GEO-CREATION.md').read_text(encoding='utf-8')
        if shared_rules not in md:
            md += '\n\n' + shared_rules
    greeting = next((line.split('：', 1)[1].strip() for line in md.splitlines() if line.startswith('开场白：')), '告诉我当前需求，我会依据本企业记录协助处理。')
    return {**AGENT_ROLES[agent_id], 'agent_id': agent_id, 'markdown': md, 'greeting': greeting, 'version': custom['version'] if custom else 1, 'customized': bool(custom)}


def manager_context(c, pid):
    s = stats(c, pid)
    knowledge = items(c, pid, 'knowledge')
    tasks = items(c, pid, 'work_task')
    automations = items(c, pid, 'automation')
    issues = []
    if not any(k['status'] == 'confirmed' for k in knowledge):
        issues.append({'text': '暂无已确认资料，内容创作缺少事实依据', 'module': 'knowledge'})
    if s['pending']:
        issues.append({'text': str(s['pending']) + ' 篇内容等待客户审核', 'module': 'content'})
    if not s['samples']:
        issues.append({'text': 'GEO 尚无采样证据，无法判断品牌提及情况', 'module': 'diagnosis'})
    if s['waiting']:
        issues.append({'text': str(s['waiting']) + ' 个渠道交付任务待处理', 'module': 'publish'})
    failed = sum(a['status'] == 'failed' for a in automations)
    if failed:
        issues.append({'text': str(failed) + ' 个自动化任务失败并暂停', 'module': 'schedule'})
    overdue = sum(bool(t['status'] != 'done' and t.get('due_at') and datetime.fromisoformat(t['due_at']) < datetime.now(timezone.utc)) for t in tasks)
    return {'project': project(c, pid)['name'], 'stats': s, 'knowledge_confirmed': sum(k['status'] == 'confirmed' for k in knowledge), 'issues': issues, 'task_count': len(tasks), 'task_done': sum(t['status'] == 'done' for t in tasks), 'task_blocked': sum(t['status'] == 'blocked' for t in tasks), 'task_overdue': overdue, 'as_of': now()}


@app.get('/api/projects/{pid}/manager')
def manager_state(pid: str, request: Request):
    with db() as c:
        user, role = scope(c, request, pid)
        return public_records({'mode': 'local', 'role': role, 'agents': [agent_soul(c, pid, a) for a in AGENT_ROLES], 'context': manager_context(c, pid), 'tasks': items(c, pid, 'work_task'), 'messages': list(reversed(items(c, pid, 'manager_message')[:80]))}, user)


class SoulInput(BaseModel):
    markdown: str = Field(min_length=20, max_length=24000)
    version: int = Field(ge=1)


@app.put('/api/projects/{pid}/agents/{agent_id}/soul')
def save_soul(pid: str, agent_id: str, body: SoulInput, request: Request):
    with db() as c:
        user, role = require_prompt_admin(c, request, pid)
        current_soul = agent_soul(c, pid, agent_id)
        if current_soul['version'] != body.version:
            raise HTTPException(409, '其他成员已修改人格配置，请刷新后编辑')
        old = next((x for x in items(c, pid, 'soul') if x['agent_id'] == agent_id), None)
        put(c, pid, 'soul_history', current_soul)
        put(c, pid, 'soul', {'agent_id': agent_id, 'markdown': body.markdown, 'version': body.version + 1}, old['id'] if old else None)
        # DB is the authoritative versioned record; this file is its editable/exportable artifact.
        folder = DB_PATH.parent / 'agents' / pid / agent_id
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / 'soul.md.tmp'
        tmp.write_text(body.markdown, encoding='utf-8')
        tmp.replace(folder / 'soul.md')
        event(c, pid, user['user_id'], '定制智能体 Soul', AGENT_ROLES[agent_id]['name'] + ' · v' + str(body.version + 1))
        return agent_soul(c, pid, agent_id)


@app.get('/api/projects/{pid}/agents/{agent_id}/soul.md')
def download_soul(pid: str, agent_id: str, request: Request):
    with db() as c:
        require_prompt_admin(c, request, pid)
        return Response(agent_soul(c, pid, agent_id)['markdown'], media_type='text/markdown; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="soul.md"'})


class ManagerChatInput(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    agent_id: str = 'director'
    intent: str = 'auto'
    request_id: str = Field(min_length=8, max_length=100)


def propose_agent(text):
    rules = [('publishing', ['发布','渠道','排期','媒介']), ('knowledge', ['资料','知识','品牌基因','图库']), ('diagnosis', ['诊断','SEO','GEO','监测']), ('leads', ['客资','询盘','线索']), ('content', ['内容','文章','创作','视频','选题'])]
    return next((agent for agent, words in rules if any(w.lower() in text.lower() for w in words)), 'director')


@app.post('/api/projects/{pid}/manager/chat')
def manager_chat(pid: str, body: ManagerChatInput, request: Request):
    if not body.text.strip() or body.intent not in ['auto', 'progress', 'blockers', 'task', 'search']:
        raise HTTPException(422, '请输入问题或需求')
    with db() as c:
        user, role = scope(c, request, pid)
        soul = agent_soul(c, pid, body.agent_id)
        existing = next((m for m in items(c, pid, 'manager_message') if m.get('request_id') == body.request_id and m.get('author_id') == user['user_id']), None)
        if existing:
            return existing
        ctx = manager_context(c, pid)
        intent = body.intent
        if intent == 'auto':
            intent = 'task' if any(w in body.text for w in ['安排','创建任务','提需求','帮我做','任务：']) else 'blockers' if any(w in body.text for w in ['卡住','问题在哪','阻塞','失败']) else 'progress' if any(w in body.text for w in ['进度','进展','待办','做了什么','汇报']) else 'search'
        links, proposal, references = [], None, []
        if intent == 'progress':
            s = ctx['stats']
            answer = f"{ctx['project']} 的当前进度：\n已确认知识 {ctx['knowledge_confirmed']} 份；内容 {s['content']} 篇，其中 {s['pending']} 篇待审核；发布回执 {s['published']} 项，待交付 {s['waiting']} 项；客资 {s['leads']} 条，有效询盘 {s['qualified']} 条。\n主管任务 {ctx['task_done']}/{ctx['task_count']} 已完成，{ctx['task_blocked']} 项阻塞，{ctx['task_overdue']} 项逾期。\n这些是当前数据库记录；发布数为人工回执，任务完成数由成员登记。"
            links = [{'label':'查看交付记录','module':'delivery'}, {'label':'查看排期','module':'schedule'}]
        elif intent == 'blockers':
            answer = '当前需要处理的事项：\n' + ('\n'.join(f"{i+1}. {x['text']}" for i,x in enumerate(ctx['issues'])) or '未发现本地规则能识别的阻塞；可以查看主管任务中的具体问题。')
            answer += '\n我可以把其中一项登记成任务，指定负责人并跟进验收。'
            links = [{'label':x['text'], 'module':x['module']} for x in ctx['issues']]
        elif intent == 'task':
            target = body.agent_id if body.agent_id != 'director' else propose_agent(body.text)
            proposal = {'title': body.text.strip()[:160], 'description': body.text.strip(), 'agent_id': target, 'acceptance': '交付对应成果，保留依据与链接，由项目成员检查后登记完成。', 'owner': '', 'due_at': ''}
            answer = '已整理为待确认的任务卡，建议交给' + AGENT_ROLES[target]['name'] + '负责。请补充执行成员、截止时间和验收标准后加入任务清单。\n目前是登记与跟踪任务，不代表专项智能体已自动执行。'
            if role not in ['owner','editor']:
                answer += '\n你当前可查看需求草案，需管理员或编辑将其加入任务清单。'
        else:
            # Grounded local lookup; no invented semantic answer when no model is connected.
            query = re.sub(r'^(查资料[：: ]*|查询[：: ]*|查一下[：: ]*)', '', body.text.strip())
            tokens = set(re.findall(r'[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]{2,}', query))
            for token in list(tokens):
                if re.fullmatch(r'[\u4e00-\u9fff]+', token):
                    tokens.update(token[i:i+2] for i in range(len(token)-1))
            docs = []
            for k in items(c, pid, 'knowledge'):
                if k['status'] == 'confirmed':
                    score = sum(len(t) for t in tokens if t.lower() in (k['title']+'\n'+k['body']).lower())
                    if score:
                        docs.append((score, k))
            docs.sort(key=lambda x:x[0], reverse=True)
            references = [{'id':k['id'], 'title':k['title'], 'version':k['version'], 'source':k['source'], 'excerpt':k['body'][:900]} for _,k in docs[:3]]
            answer = '找到以下已确认资料，供你核对。下面是原文摘录，不是生成式回答。' if references else '当前企业已确认资料中未找到直接匹配的依据。可以补充产品名或关键词，或把需求加入任务清单。\n目前未接通大模型，复杂推理、自动拆解与跨模块执行还不能由对话独立完成。'
            links = [{'label':'进入智库问答','module':'qa'}]
        message = {'request_id':body.request_id, 'author_id':user['user_id'], 'agent_id':body.agent_id, 'soul_version':soul['version'], 'mode':'local', 'question':body.text, 'answer':answer, 'intent':intent, 'links':links, 'references':references, 'proposal':proposal, 'task_id':'', 'as_of':ctx['as_of']}
        rid = put(c, pid, 'manager_message', message)
        return {'id': rid, **message}


class WorkTaskInput(BaseModel):
    message_id: str = ''
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default='', max_length=5000)
    agent_id: str = 'director'
    owner: str = Field(default='', max_length=120)
    due_at: str = ''
    acceptance: str = Field(min_length=2, max_length=3000)


@app.post('/api/projects/{pid}/manager/tasks')
def create_work_task(pid: str, body: WorkTaskInput, request: Request):
    with db() as c:
        user, role = scope(c, request, pid, ['owner','editor'])
        agent_soul(c, pid, body.agent_id)
        msg = resource(c, pid, body.message_id, 'manager_message') if body.message_id else None
        if msg and msg.get('task_id'):
            return {'id':msg['task_id']}
        if body.due_at:
            try:
                deadline = datetime.fromisoformat(body.due_at)
                if deadline.tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, '截止时间需要有效日期和时区')
        rid = put(c, pid, 'work_task', {**body.model_dump(), 'status':'todo', 'revision':1, 'result':'', 'created_by':user['user_id'], 'history':[]})
        if msg:
            msg['task_id'] = rid
            put(c, pid, 'manager_message', msg, body.message_id)
        event(c, pid, user['user_id'], '主管登记项目任务', body.title + ' · '+AGENT_ROLES[body.agent_id]['name'])
        return {'id':rid}


class WorkTaskUpdate(BaseModel):
    status: str
    result: str = Field(default='', max_length=5000)
    revision: int


@app.put('/api/projects/{pid}/manager/tasks/{rid}')
def update_work_task(pid: str, rid: str, body: WorkTaskUpdate, request: Request):
    if body.status not in ['todo','doing','blocked','done']:
        raise HTTPException(422, '无效任务状态')
    if body.status in ['blocked','done'] and not body.result.strip():
        raise HTTPException(422, '请记录阻塞原因或完成成果，再更新状态')
    with db() as c:
        user, role = scope(c, request, pid, ['owner','editor'])
        t = resource(c, pid, rid, 'work_task')
        check_revision(t, body.revision)
        t['history'].append({'status':t['status'], 'result':t['result'], 'at':now(), 'actor':user['user_id']})
        t.update(status=body.status, result=body.result, revision=t['revision']+1)
        put(c, pid, 'work_task', t, rid)
        event(c, pid, user['user_id'], '更新主管任务', t['title']+' · '+body.status)
        return {'ok':True}


import delivery_runtime
delivery = delivery_runtime.register(globals())
import format_skills
format_skills.register(globals())
import customer_report
customer_report.register(globals())
import sample_review
sample_review.register(globals())
import account_activation
create_account_invite = account_activation.register(globals())
import video_composer
video_composition = video_composer.register(globals())

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')
