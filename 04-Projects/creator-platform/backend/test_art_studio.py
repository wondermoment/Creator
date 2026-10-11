import uuid
from unittest.mock import patch, AsyncMock
import httpx
from backend import test_commerce

class ArtTest(test_commerce.CommerceTest):
    def test_generation_idempotency_and_outputs(self):
        body = dict(request_key=str(uuid.uuid4()),kind='painting',prompt='安静的森林水彩画',consent=True)
        fake = AsyncMock()
        fake.post.return_value = httpx.Response(200,json={'request_id':'test-remote'})
        fake.get.return_value = httpx.Response(200,json={'status':'completed','outputs':['https://example.com/painting.png']},request=httpx.Request('GET','https://example.com'))
        with patch('backend.app.art_studio.key',return_value='test'),patch('backend.app.art_studio.httpx.AsyncClient') as client:
            client.return_value.__aenter__.return_value=fake
            r=self.client.post('/api/art/create',json=body)
            self.assertEqual(r.status_code,200)
            self.client.post('/api/art/create',json=body)
            self.assertEqual(fake.post.call_count,1)
            finished=self.client.get('/api/art/works/'+body['request_key']).json()
            self.assertEqual(finished['status'],'completed')
            self.assertEqual(len(finished['outputs']),1)
            self.assertNotIn('remote_id',finished)

    def test_rejected_key_and_consent(self):
        body=dict(request_key=str(uuid.uuid4()),kind='music',prompt='温柔的钢琴',consent=False)
        self.assertEqual(self.client.post('/api/art/create',json=body).status_code,422)
        body['consent']=True
        fake=AsyncMock()
        fake.post.return_value=httpx.Response(403,json={'detail':'Invalid key'})
        with patch('backend.app.art_studio.key',return_value='test'),patch('backend.app.art_studio.httpx.AsyncClient') as client:
            client.return_value.__aenter__.return_value=fake
            r=self.client.post('/api/art/create',json=body)
            self.assertEqual(r.status_code,502)
            self.assertIn('密钥无效',r.json()['detail'])
        self.assertEqual(self.client.get('/api/art/works').json()[0]['status'],'failed')
