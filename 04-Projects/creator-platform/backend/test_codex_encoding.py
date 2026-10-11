import unittest,json,tempfile,subprocess
from unittest.mock import patch
from backend.app.local_codex import decode_output,generate,CodexLocalError
class EncodingTests(unittest.TestCase):
 def test_utf8_and_gb18030_lossless(self):
  for enc in ('utf-8','gb18030'):
   self.assertEqual(decode_output('在呀，我是小乔。'.encode(enc)),'在呀，我是小乔。')
 def test_corrupt_and_replacement_rejected(self):
  for raw in (b'\xff', '\ufffd'.encode()):
   with self.assertRaises(CodexLocalError):decode_output(raw)
 def test_json_escape_replacement_rejected(self):
  with tempfile.TemporaryDirectory() as d,patch('backend.app.local_codex.availability',return_value={'available':True}),patch('backend.app.local_codex.command',return_value=['codex']),patch('backend.app.local_codex.subprocess.run') as run:
   lines=[{'type':'item.completed','item':{'type':'agent_message','text':'\ufffd'}},{'type':'turn.completed'}]
   run.return_value=subprocess.CompletedProcess([],0,('\n'.join(json.dumps(x) for x in lines)).encode(),b'')
   with self.assertRaises(CodexLocalError):generate(d,'test',None,[{'role':'user','content':'你好'}])
   self.assertIsInstance(run.call_args.kwargs['input'],bytes)
   args=run.call_args.args[0]
   self.assertIn('model_provider="chatgpt_https"',args)
   self.assertIn('model_providers.chatgpt_https.requires_openai_auth=true',args)
   self.assertIn('model_providers.chatgpt_https.supports_websockets=false',args)
   self.assertIn('model_providers.chatgpt_https.base_url="https://chatgpt.com/backend-api/codex"',args)
   self.assertIn('forced_login_method="chatgpt"',args)
   self.assertIn('read-only',args)
   self.assertNotIn('OPENAI_API_KEY',run.call_args.kwargs['env'])
if __name__=='__main__':unittest.main()
