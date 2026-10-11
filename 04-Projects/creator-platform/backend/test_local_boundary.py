import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import main
def with_peer(app, peer='127.0.0.1'):
 async def wrapped(scope,receive,send):
  if scope['type']=='http':scope={**scope,'client':(peer,50000)}
  await app(scope,receive,send)
 return wrapped

class LocalBoundaryTest(unittest.TestCase):
 def test_requests_rejected_before_database_or_model(self):
  with patch.object(main,'db',side_effect=AssertionError('must not read data')):
   for peer,base,headers in [ ('198.51.100.3','http://127.0.0.1',{}),('127.0.0.1','http://evil.example',{}),('127.0.0.1','http://127.0.0.1',{'Origin':'https://evil.example'}),('127.0.0.1','http://127.0.0.1',{'Origin':'null'}),('127.0.0.1','http://127.0.0.1',{'Sec-Fetch-Site':'cross-site'}) ]:
    with self.subTest(peer=peer,base=base,headers=headers):
     c=TestClient(with_peer(main.app,peer),base_url=base)
     for path in ['/api/overview','/api/patients/p1','/api/courses','/api/commerce/catalog']:
      self.assertEqual(c.get(path,headers=headers).status_code,403)
     self.assertEqual(c.post('/api/patients/p1/review',headers=headers).status_code,403)
     self.assertEqual(c.post('/api/coaches/qiao/chat',json={'question':'test'},headers=headers).status_code,403)
 def test_same_origin_loopback_can_read(self):
  old=main.RUNTIME
  try:
   with tempfile.TemporaryDirectory() as d:
    main.RUNTIME=Path(d)
    with TestClient(with_peer(main.app),base_url='http://127.0.0.1') as c:
     self.assertEqual(c.get('/api/overview',headers={'Origin':'http://127.0.0.1','Sec-Fetch-Site':'same-origin'}).status_code,200)
     self.assertEqual(c.get('/').status_code,200)
  finally:main.RUNTIME=old
if __name__=='__main__':unittest.main()

