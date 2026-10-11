"""Loopback-only commerce sandbox. No payment credentials or real transfers."""
import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


def local_only(request: Request):
    if not request.client or request.client.host not in ('127.0.0.1', '::1'):
        raise HTTPException(403, '本地演示仅允许本机访问；正式部署须先接入身份与权限系统')
    if request.url.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise HTTPException(403, '不允许此访问域名')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, '不允许跨站访问本地演示')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, '不允许跨站访问本地演示')


router = APIRouter(prefix='/api/commerce', dependencies=[Depends(local_only)])
connect = None
CATALOG = [
    {'id': 'oats', 'name': '原味全谷燕麦 · 测试商品', 'price': 3900, 'stock': 50},
    {'id': 'tea', 'name': '无糖茶饮 · 测试商品', 'price': 2900, 'stock': 50},
    {'id': 'olive-oil', 'name': '橄榄油 · 测试商品', 'price': 8900, 'stock': 50},
]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def audit(c, kind, payload):
    c.execute('INSERT INTO commerce_audit VALUES (?,?,?,?)',
              (str(uuid.uuid4()), kind, json.dumps(payload, ensure_ascii=False), stamp()))


def initialize(db):
    global connect
    connect = db
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS shop_products(id TEXT PRIMARY KEY,name TEXT,price INTEGER CHECK(price>0),stock INTEGER CHECK(stock>=0));
        CREATE TABLE IF NOT EXISTS shop_agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,parent_id TEXT REFERENCES shop_agents(id),created_at TEXT);
        CREATE TABLE IF NOT EXISTS shop_orders(id TEXT PRIMARY KEY,request_key TEXT UNIQUE,product_id TEXT REFERENCES shop_products(id),quantity INTEGER,total INTEGER,status TEXT,agent1 TEXT REFERENCES shop_agents(id),agent2 TEXT REFERENCES shop_agents(id),rate1 INTEGER,rate2 INTEGER,created_at TEXT);
        CREATE TABLE IF NOT EXISTS shop_ledger(id TEXT PRIMARY KEY,order_id TEXT REFERENCES shop_orders(id),agent_id TEXT REFERENCES shop_agents(id),level INTEGER,amount INTEGER,status TEXT,UNIQUE(order_id,level));
        CREATE TABLE IF NOT EXISTS shop_transfers(id TEXT PRIMARY KEY,order_id TEXT UNIQUE REFERENCES shop_orders(id),status TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS commerce_audit(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS shop_content(id TEXT PRIMARY KEY REFERENCES shop_products(id),category TEXT,description TEXT,ingredients TEXT,usage TEXT,cautions TEXT,status TEXT);
        ''')
        for p in CATALOG:
            c.execute('INSERT OR IGNORE INTO shop_products VALUES (?,?,?,?)', tuple(p.values()))
        c.execute('INSERT OR IGNORE INTO shop_agents VALUES (?,?,?,?)', ('demo-a', '示例代理 A', None, stamp()))
        c.execute('INSERT OR IGNORE INTO shop_agents VALUES (?,?,?,?)', ('demo-b', '示例代理 B', 'demo-a', stamp()))


class StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Agent(StrictBody):
    name: str = Field(min_length=1, max_length=40)
    parent_id: str | None = None


class Order(StrictBody):
    product_id: str
    quantity: int = Field(strict=True, ge=1, le=20)
    referral: str | None = None
    request_key: uuid.UUID


class ProductContent(StrictBody):
    name: str = Field(min_length=2, max_length=80)
    price: int = Field(strict=True, ge=1, le=10000000)
    stock: int = Field(strict=True, ge=0, le=100000)
    category: Literal['食物','有机蔬菜','饮品','调味料','基础营养素','长寿抗衰','智能硬件','精准检测']
    description: str = Field(min_length=10, max_length=3000)
    ingredients: str = Field(min_length=2, max_length=1000)
    usage: str = Field(min_length=2, max_length=1000)
    cautions: str = Field(min_length=2, max_length=1000)
    status: Literal['draft','published'] = 'draft'
    expected_revision: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')


PRODUCT_SELECT = 'SELECT p.*,x.category,x.description,x.ingredients,x.usage,x.cautions,x.status FROM shop_products p JOIN shop_content x ON x.id=p.id'
PRODUCT_REVISION_FIELDS = ('id','name','price','stock','category','description','ingredients','usage','cautions','status')


def product_revision(product):
    # Hash only fields this form can replace; image uploads are independent.
    raw = json.dumps([product[k] for k in PRODUCT_REVISION_FIELDS], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


@router.get('/catalog')
def catalog():
    with connect() as c:
        rows = [dict(r) for r in c.execute(PRODUCT_SELECT)]
        images = {r['id'] for r in c.execute('SELECT id FROM product_images')}
        return [{**r, 'has_image': int(r['id'] in images), 'revision': product_revision(r)} for r in rows]


@router.put('/products/{pid}')
def save_product(pid: str, body: ProductContent):
    if not re.fullmatch(r'custom-[A-Za-z0-9][A-Za-z0-9_-]{0,72}', pid):
        raise HTTPException(422, '请使用后台生成的商品编号')
    for value in (body.name,body.description,body.ingredients,body.usage,body.cautions):
        if not value.strip():
            raise HTTPException(422, '内容不能仅为空格')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        current = c.execute(PRODUCT_SELECT+' WHERE p.id=?', (pid,)).fetchone()
        exists = c.execute('SELECT 1 FROM shop_products WHERE id=?', (pid,)).fetchone()
        if exists and (not current or body.expected_revision != product_revision(current)):
            raise HTTPException(409, '商品内容或库存已变更。请复制保留当前修改，关闭编辑框后刷新页面，再核对最新内容重新编辑。')
        if not exists and body.expected_revision is not None:
            raise HTTPException(409, '商品已不存在，请刷新页面后核对，不会自动重新创建。')
        c.execute('INSERT INTO shop_products VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,price=excluded.price,stock=excluded.stock', (pid,body.name.strip(),body.price,body.stock))
        c.execute('INSERT INTO shop_content VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET category=excluded.category,description=excluded.description,ingredients=excluded.ingredients,usage=excluded.usage,cautions=excluded.cautions,status=excluded.status', (pid,body.category,body.description,body.ingredients,body.usage,body.cautions,body.status))
        audit(c,'product.saved',{'id':pid,'status':body.status})
    return {'id':pid,'status':body.status}


@router.get('/snapshot')
def snapshot():
    with connect() as c:
        return {'mode': 'sandbox', 'live_payment': False, 'rates': [1000, 500],
                **{key: [dict(r) for r in c.execute(sql)] for key, sql in {
                    'products': 'SELECT * FROM shop_products',
                    'agents': 'SELECT * FROM shop_agents ORDER BY created_at',
                    'orders': 'SELECT * FROM shop_orders ORDER BY created_at DESC LIMIT 100',
                    'ledger': 'SELECT * FROM shop_ledger',
                    'transfers': 'SELECT * FROM shop_transfers ORDER BY created_at DESC',
                    'audit': 'SELECT * FROM commerce_audit ORDER BY created_at DESC LIMIT 50',
                }.items()}}


@router.post('/agents', status_code=201)
def agent_create(body: Agent):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, '请填写代理名称')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if body.parent_id and not c.execute('SELECT 1 FROM shop_agents WHERE id=?', (body.parent_id,)).fetchone():
            raise HTTPException(422, '上级代理不存在')
        aid = 'agent-' + uuid.uuid4().hex[:12]
        c.execute('INSERT INTO shop_agents VALUES (?,?,?,?)', (aid, name, body.parent_id, stamp()))
        audit(c, 'agent.created', {'id': aid, 'parent_id': body.parent_id})
    return {'id': aid}


@router.post('/orders', status_code=201)
def order_create(body: Order):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        previous = c.execute('SELECT * FROM shop_orders WHERE request_key=?', (str(body.request_key),)).fetchone()
        if previous:
            if (previous['product_id'], previous['quantity'], previous['agent1']) != (body.product_id, body.quantity, body.referral):
                raise HTTPException(409, '同一请求标识不能用于不同订单')
            return dict(previous)
        p = c.execute('SELECT * FROM shop_products WHERE id=?', (body.product_id,)).fetchone()
        content = c.execute('SELECT status FROM shop_content WHERE id=?', (body.product_id,)).fetchone()
        if content and content['status'] != 'published':
            raise HTTPException(409, '该商品未上架')
        if not p:
            raise HTTPException(409, '该商品尚未配置可售规格和价格')
        parent = None
        if body.referral:
            a = c.execute('SELECT * FROM shop_agents WHERE id=?', (body.referral,)).fetchone()
            if not a:
                raise HTTPException(422, '推荐代理不存在')
            parent = a['parent_id']
        changed = c.execute('UPDATE shop_products SET stock=stock-? WHERE id=? AND stock>=?', (body.quantity, body.product_id, body.quantity)).rowcount
        if not changed:
            raise HTTPException(409, '测试库存不足')
        oid = uuid.uuid4().hex
        c.execute('INSERT INTO shop_orders VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                  (oid, str(body.request_key), body.product_id, body.quantity, p['price'] * body.quantity, 'pending', body.referral, parent, 1000, 500, stamp()))
        audit(c, 'order.created', {'id': oid, 'mode': 'sandbox'})
        return dict(c.execute('SELECT * FROM shop_orders WHERE id=?', (oid,)).fetchone())


@router.post('/orders/{oid}/{action}')
def order_action(oid: str, action: str):
    if action not in ('simulate-pay', 'simulate-settle', 'refund', 'cancel'):
        raise HTTPException(400, '真实支付与分账尚未启用')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM shop_orders WHERE id=?', (oid,)).fetchone()
        if not row:
            raise HTTPException(404, '订单不存在')
        o = dict(row)
        target = {'simulate-pay': 'paid', 'simulate-settle': 'settled', 'refund': 'refunded', 'cancel': 'cancelled'}[action]
        if o['status'] == target or (action == 'simulate-pay' and o['status'] == 'settled'):
            return {'status': o['status'], 'idempotent': True, 'mode': 'sandbox'}
        allowed = {'simulate-pay': ['pending'], 'simulate-settle': ['paid'], 'refund': ['paid', 'settled'], 'cancel': ['pending']}
        if o['status'] not in allowed[action]:
            raise HTTPException(409, '当前订单状态不允许此操作')
        if action == 'simulate-pay':
            for level in (1, 2):
                aid = o[f'agent{level}']
                if aid:
                    c.execute('INSERT INTO shop_ledger VALUES (?,?,?,?,?,?)', (uuid.uuid4().hex, oid, aid, level, o['total'] * o[f'rate{level}'] // 10000, 'held'))
        elif action == 'simulate-settle':
            c.execute("UPDATE shop_ledger SET status='simulated' WHERE order_id=?", (oid,))
            c.execute('INSERT INTO shop_transfers VALUES (?,?,?,?)', (uuid.uuid4().hex, oid, 'simulated_no_money_moved', stamp()))
        else:
            c.execute('UPDATE shop_products SET stock=stock+? WHERE id=?', (o['quantity'], o['product_id']))
            if action == 'refund':
                c.execute("UPDATE shop_ledger SET status='reversed' WHERE order_id=?", (oid,))
                c.execute("UPDATE shop_transfers SET status='simulated_reversed' WHERE order_id=?", (oid,))
        c.execute('UPDATE shop_orders SET status=? WHERE id=?', (target, oid))
        audit(c, 'order.' + action, {'id': oid, 'from': o['status'], 'to': target, 'mode': 'sandbox'})
    return {'status': target, 'mode': 'sandbox'}
