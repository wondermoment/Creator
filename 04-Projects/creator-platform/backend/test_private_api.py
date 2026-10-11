import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import main,book_chat
from backend.test_local_boundary import with_peer
class PrivateApiTest(unittest.TestCase):
 def test_sensitive_success_and_handled_errors_not_cached(self):
  with tempfile.TemporaryDirectory() as d,patch.object(main,'RUNTIME',Path(d)),patch.object(book_chat,'ROOT',Path(d)/'books'):
   with TestClient(with_peer(main.app),base_url='http://127.0.0.1') as c:
    responses=[c.get('/api/overview'),c.get('/api/patients/p1'),c.get('/api/books/sample/history'),c.get('/api/patients/missing'),c.get('/api/overview',headers={'Origin':'https://elsewhere.example'}),c.post('/api/coaches/qiao/chat',json={'question':''})]
    self.assertEqual([r.status_code for r in responses],[200,200,200,404,403,422])
    for r in responses:
     self.assertEqual(r.headers['cache-control'],'no-store, private')
     self.assertEqual(r.headers['x-content-type-options'],'nosniff')
 def test_report_download_keeps_attachment_and_private_cache(self):
  with tempfile.TemporaryDirectory() as d,patch.object(main,'RUNTIME',Path(d)):
   with TestClient(with_peer(main.app),base_url='http://127.0.0.1') as c:
    # Synthetic signature-only document: tests delivery, not PDF validity.
    data=b'%PDF-1.4 synthetic attachment'
    r=c.post('/api/patients/p1/reports',files={'file':('sample.pdf',data,'application/pdf')})
    self.assertEqual(r.status_code,201)
    download=c.get('/api/reports/'+r.json()['id'])
    self.assertEqual(download.content,data)
    self.assertIn('attachment',download.headers['content-disposition'])
    self.assertEqual(download.headers['cache-control'],'no-store, private')
    asset=c.get('/static/coach-chat.js')
    self.assertEqual(asset.status_code,200)
    self.assertNotIn('no-store',asset.headers.get('cache-control',''))
if __name__=='__main__':unittest.main()
