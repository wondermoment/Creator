import io
import uuid
from PIL import Image
from backend import test_commerce


class ExperienceTest(test_commerce.CommerceTest):
    def test_inquiry_receipt_followup_and_conflict(self):
        body = dict(request_key=str(uuid.uuid4()), subject='测试商品', kind='报价', need='了解规格')
        first = self.client.post('/api/commerce/inquiries', json=body)
        self.assertEqual(first.status_code, 200)
        rid = first.json()['id']
        self.assertEqual(self.client.post('/api/commerce/inquiries', json=body).json()['id'], rid)
        body['need'] = '修改内容'
        self.assertEqual(self.client.post('/api/commerce/inquiries', json=body).status_code, 409)
        route = '/api/commerce/inquiries/' + rid
        self.assertEqual(self.client.patch(route, json=dict(status='closed', note='完成', expected_version=1)).status_code, 422)
        self.assertEqual(self.client.patch(route, json=dict(status='following', note='已受理，核实规格中', expected_version=1)).status_code, 200)
        self.assertEqual(self.client.patch(route, json=dict(status='closed', note='完成', expected_version=1)).status_code, 409)
        self.assertEqual(self.client.patch(route, json=dict(status='closed', note='规格已说明', expected_version=2)).status_code, 200)
        rows = self.client.get('/api/commerce/inquiries').json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['timeline']), 3)
        self.assertEqual(rows[0]['status'], 'closed')

    def test_product_image_validation_and_catalog(self):
        pid = 'custom-image-test'
        product = dict(name='测试主图商品', price=100, stock=1, category='食物', description='这是测试商品的详细说明文字', ingredients='测试成分', usage='测试用法', cautions='仅作测试', status='draft')
        self.assertEqual(self.client.put('/api/commerce/products/'+pid, json=product).status_code, 200)
        route = '/api/commerce/products/'+pid+'/image'
        self.assertEqual(self.client.post(route, files={'file': ('bad.png', b'<script>alert(1)</script>', 'image/png')}).status_code, 422)
        out = io.BytesIO()
        Image.new('RGB', (1800, 900), 'yellow').save(out, 'PNG')
        self.assertEqual(self.client.post(route, files={'file': ('sample.png', out.getvalue(), 'image/png')}).status_code, 200)
        response = self.client.get(route)
        self.assertEqual(response.headers['content-type'], 'image/jpeg')
        with Image.open(io.BytesIO(response.content)) as im:
            self.assertEqual(im.size, (1400, 700))
        self.assertEqual(self.client.get('/api/commerce/catalog').json()[0]['has_image'], 1)
        self.assertEqual(self.client.post('/api/commerce/orders', json=dict(product_id=pid, quantity=1, request_key=str(uuid.uuid4()))).status_code, 409)

