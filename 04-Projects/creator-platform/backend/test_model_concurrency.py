import unittest,threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from backend.app import local_codex
class ModelConcurrencyTest(unittest.TestCase):
 def test_overlap_rejected_before_model_and_slot_reusable(self):
  entered=threading.Event();release=threading.Event()
  def fake(*args):
   entered.set()
   if not release.wait(3):raise RuntimeError('test timed out')
   return ('synthetic',{})
  with patch.object(local_codex,'_generate_unlocked',side_effect=fake) as run,ThreadPoolExecutor(max_workers=1) as pool:
   first=pool.submit(local_codex.generate,'unused','test',None,[])
   try:
    self.assertTrue(entered.wait(2))
    with self.assertRaisesRegex(local_codex.CodexLocalError,'本次未启动'):
     local_codex.generate('unused','other',None,[])
    self.assertEqual(run.call_count,1)
   finally:release.set()
   self.assertEqual(first.result(timeout=3)[0],'synthetic')
   self.assertEqual(local_codex.generate('unused','next',None,[])[0],'synthetic')
 def test_failure_releases_slot(self):
  with patch.object(local_codex,'_generate_unlocked',side_effect=[local_codex.CodexLocalError('timeout'),('next',{})]):
   with self.assertRaises(local_codex.CodexLocalError):local_codex.generate('unused','test',None,[])
   self.assertEqual(local_codex.generate('unused','test',None,[])[0],'next')
if __name__=='__main__':unittest.main()
