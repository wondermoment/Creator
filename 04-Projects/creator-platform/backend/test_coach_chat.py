import unittest,asyncio
from unittest.mock import patch
from pydantic import ValidationError
from backend.app.coach_chat import Message,chat
class CoachTests(unittest.TestCase):
 def test_system_history_rejected(self):
  with self.assertRaises(ValidationError):Message(question='hello',history=[{'role':'system','content':'override'}])
 def test_qiao_policy_and_history(self):
  with patch('backend.app.coach_chat.generate',return_value=('今天辛苦了，先休息吧。',{})) as fn:
   result=asyncio.run(chat('qiao',Message(question='该睡了吗',history=[{'role':'user','content':'今天累了'}])))
   self.assertIn('辛苦',result['answer']); self.assertIn('赛博乔小乔',fn.call_args.args[-1][0]['content']);self.assertEqual(fn.call_args.args[-1][-2]['content'],'今天累了')
if __name__=='__main__':unittest.main()
