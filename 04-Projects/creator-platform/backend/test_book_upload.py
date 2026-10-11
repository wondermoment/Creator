import asyncio,io,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from fastapi import UploadFile,HTTPException
from backend.app import book_chat
class BookUploadTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.patch=patch.object(book_chat,'ROOT',self.root);self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def send(self,data,name='book.txt'):
  f=UploadFile(file=io.BytesIO(data),filename=name)
  try:return asyncio.run(book_chat.upload('test-book',f))
  finally:self.assertTrue(f.file.closed)
 def test_text_and_portable_name(self):
  self.send('测试原文'.encode(),r'C:\private\book.txt')
  s=book_chat.source('test-book');self.assertEqual(s['name'],'book.txt');self.assertEqual(s['chunks'][0]['text'],'测试原文')
 def test_rejections_preserve_source(self):
  self.send(b'original');before=(self.root/'test-book.json').read_bytes()
  for data,name,status in [(b'','empty.txt',422),(b'\xff','bad.txt',422),(b'bad','bad.exe',422),(b'x'*(10*1024*1024+1),'big.txt',413),(b'x'*2000001,'long.txt',413)]:
   with self.subTest(name=name),self.assertRaises(HTTPException) as err:self.send(data,name)
   self.assertEqual(err.exception.status_code,status)
   self.assertEqual((self.root/'test-book.json').read_bytes(),before)
 def test_write_failure_preserves_original_and_cleans_staging(self):
  self.send(b'original');before=(self.root/'test-book.json').read_bytes()
  with patch.object(book_chat.json,'dump',side_effect=OSError('disk full')):
   with self.assertRaises(OSError):self.send(b'new')
  self.assertEqual((self.root/'test-book.json').read_bytes(),before)
  self.assertEqual(list(self.root.glob('*.tmp')),[])
if __name__=='__main__':unittest.main()
