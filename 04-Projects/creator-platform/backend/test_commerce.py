import tempfile
import unittest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import main, commerce


class CommerceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = main.RUNTIME
        main.RUNTIME = Path(self.temp.name)
        main.app.dependency_overrides[commerce.local_only] = lambda: None
        self.context = TestClient(main.app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        main.app.dependency_overrides.clear()
        main.RUNTIME = self.old
        self.temp.cleanup()

    def order(self, **kwargs):
        body = dict(product_id='oats', quantity=2, referral='demo-b', request_key=str(uuid.uuid4()))
        body.update(kwargs)
        return self.client.post('/api/commerce/orders', json=body)

    def action(self, oid, action):
        return self.client.post(f'/api/commerce/orders/{oid}/{action}')

    def snapshot(self):
        return self.client.get('/api/commerce/snapshot').json()

    def test_payment_idempotency_settlement_and_refund(self):
        o = self.order().json()
        self.assertEqual(o['total'], 7800)
        self.assertEqual(self.snapshot()['ledger'], [])
        self.assertEqual(self.action(o['id'], 'simulate-settle').status_code, 409)
        for _ in range(2):
            self.assertEqual(self.action(o['id'], 'simulate-pay').status_code, 200)
        ledger = self.snapshot()['ledger']
        self.assertEqual(len(ledger), 2)
        self.assertEqual({l['level']: l['amount'] for l in ledger}, {1:780, 2:390})
        for _ in range(2):
            self.assertEqual(self.action(o['id'], 'simulate-settle').status_code, 200)
        self.assertEqual(len(self.snapshot()['transfers']), 1)
        for _ in range(2):
            self.assertEqual(self.action(o['id'], 'refund').status_code, 200)
        self.assertTrue(all(l['status']=='reversed' for l in self.snapshot()['ledger']))
        self.assertEqual(next(p['stock'] for p in self.snapshot()['products'] if p['id']=='oats'), 50)
        self.assertEqual(self.action(o['id'], 'simulate-pay').status_code, 409)

    def test_duplicate_order_and_price_tampering(self):
        key = str(uuid.uuid4())
        first = self.order(request_key=key).json()
        self.assertEqual(self.order(request_key=key).json()['id'], first['id'])
        self.assertEqual(self.order(request_key=key, quantity=3).status_code, 409)
        self.assertEqual(self.order(total=1).status_code, 422)
        self.assertEqual(self.order(quantity=0).status_code, 422)
        self.assertEqual(self.order(quantity=1.5).status_code, 422)
        self.assertEqual(self.order(product_id='nmn').status_code, 409)
        self.assertEqual(self.order(referral='missing').status_code, 422)

    def test_two_levels_only_and_no_recruitment_commissions(self):
        a = self.client.post('/api/commerce/agents', json={'name':'测试 C','parent_id':'demo-b'}).json()['id']
        self.assertEqual(self.snapshot()['ledger'], [])
        o = self.order(referral=a).json()
        self.action(o['id'], 'simulate-pay')
        self.assertEqual({l['agent_id'] for l in self.snapshot()['ledger']}, {a,'demo-b'})

    def test_no_referral_no_commission_and_cancel(self):
        o = self.order(referral=None).json()
        self.action(o['id'], 'simulate-pay')
        self.assertEqual(self.snapshot()['ledger'], [])
        o = self.order().json()
        self.action(o['id'], 'cancel')
        self.action(o['id'], 'cancel')
        self.assertEqual(self.action(o['id'], 'simulate-pay').status_code, 409)

    def test_stock_and_local_gate(self):
        for _ in range(2):
            self.assertEqual(self.order(quantity=20).status_code, 201)
        self.assertEqual(self.order(quantity=20).status_code, 409)
        main.app.dependency_overrides.clear()
        self.assertEqual(self.client.get('/api/commerce/snapshot').status_code, 403)

    def test_content_product_publish_and_unpublish(self):
        body=dict(name='测试内容商品',price=1900,stock=4,category='食物',description='这是足够长度的内容商品介绍',ingredients='成分与规格待核实',usage='测试使用说明',cautions='测试不发货',status='draft')
        self.assertEqual(self.client.put('/api/commerce/products/custom-test',json=body).status_code,200)
        self.assertEqual(self.order(product_id='custom-test').status_code,409)
        revision=self.client.get('/api/commerce/catalog').json()[0]['revision']
        self.assertEqual(self.client.put('/api/commerce/products/custom-test',json={**body,'status':'published','expected_revision':revision}).status_code,200)
        self.assertEqual(self.order(product_id='custom-test').status_code,201)
        self.assertEqual(self.client.get('/api/commerce/catalog').json()[0]['description'],body['description'])

    def test_product_id_rejects_markup_and_url_delimiters_without_writes(self):
        from urllib.parse import quote
        body = dict(name='合成商品',price=1900,stock=4,category='食物',description='合成测试商品介绍内容文字',ingredients='合成规格',usage='合成使用',cautions='测试不发货')
        before = self.snapshot()
        for pid in ('custom-', 'custom-" autofocus onfocus="alert(1)',
                    'custom-<svg onload=alert(1)>', 'custom-a?b', 'custom-a#b',
                    'custom-a%22', 'custom-a b', 'custom-中文', 'custom-'+'a'*74):
            with self.subTest(pid=pid):
                response = self.client.put('/api/commerce/products/'+quote(pid,safe=''),json=body)
                self.assertEqual(response.status_code,422)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.client.get('/api/commerce/catalog').json(),[])
        for pid in ('custom-'+str(uuid.uuid4()), 'custom-test_01', 'custom-'+'a'*73):
            self.assertEqual(self.client.put('/api/commerce/products/'+pid,json=body).status_code,200)

    def test_stale_product_form_cannot_restore_order_stock_or_overwrite_content(self):
        route='/api/commerce/products/custom-stock-test'
        body=dict(name='合成库存商品',price=1900,stock=4,category='食物',description='这是合成库存商品说明文字',ingredients='合成规格',usage='合成用法',cautions='测试不发货',status='published')
        self.assertEqual(self.client.put(route,json=body).status_code,200)
        old=self.client.get('/api/commerce/catalog').json()[0]['revision']
        self.assertEqual(self.order(product_id='custom-stock-test',quantity=2).status_code,201)
        before=self.snapshot()
        for update in (body,{**body,'expected_revision':old}):
            self.assertEqual(self.client.put(route,json=update).status_code,409)
            self.assertEqual(self.snapshot(),before)
        current=self.client.get('/api/commerce/catalog').json()[0]
        self.assertEqual(current['stock'],2)
        self.assertNotEqual(current['revision'],old)
        update={**body,'stock':2,'description':'更新后的合成商品介绍文字','expected_revision':current['revision']}
        self.assertEqual(self.client.put(route,json=update).status_code,200)
        after=self.snapshot()
        self.assertEqual(self.client.put(route,json={**update,'name':'另一个旧表单'}).status_code,409)
        self.assertEqual(self.snapshot(),after)
        self.assertEqual(self.client.put('/api/commerce/products/custom-missing',json=update).status_code,409)

    def test_two_simultaneous_product_editors_only_one_wins(self):
        from concurrent.futures import ThreadPoolExecutor
        route='/api/commerce/products/custom-race'
        body=dict(name='合成并发商品',price=1900,stock=4,category='食物',description='这是合成并发商品说明文字',ingredients='合成规格',usage='合成用法',cautions='测试不发货')
        self.assertEqual(self.client.put(route,json=body).status_code,200)
        revision=self.client.get('/api/commerce/catalog').json()[0]['revision']
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda name:self.client.put(route,json={**body,'name':name,'expected_revision':revision}),['编辑甲商品','编辑乙商品']))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        self.assertEqual(len([a for a in self.snapshot()['audit'] if a['kind']=='product.saved']),2)


if __name__ == '__main__':
    unittest.main()
