import io
import json
import tempfile
import threading
import unittest
import asyncio
import httpx
from unittest.mock import patch
from backend.app.local_codex_stream import generate_stream, CodexLocalError

class Pipe(io.BytesIO):
    def close(self):
        self.saved = self.getvalue()
        super().close()

class Process:
    pid = 123456
    def __init__(self, events):
        self.stdin = Pipe()
        self.stdout = Pipe(('\n'.join(json.dumps(e) for e in events)+'\n').encode())
    def poll(self):
        return 0
    def wait(self, timeout=None):
        return 0

class StreamTests(unittest.TestCase):
    def test_midstream_cancellation_cleans_up_and_releases_slot(self):
        from backend.app.local_codex import _generation_slot
        proc=Process([
            {'id':1,'result':{}},{'id':2,'result':{'thread':{'id':'synthetic'}}},{'id':3,'result':{}},
            {'method':'item/agentMessage/delta','params':{'itemId':'a','delta':'合成未完成'}}])
        cancelled=threading.Event()
        with tempfile.TemporaryDirectory() as root, patch('backend.app.local_codex_stream.command',return_value=['codex']), patch('backend.app.local_codex_stream.subprocess.Popen',return_value=proc), patch('backend.app.local_codex_stream.stop_process') as stop:
            stream=generate_stream(root,[{'role':'user','content':'合成'}],cancelled)
            self.assertEqual(next(stream)['type'],'delta')
            cancelled.set()
            self.assertEqual(list(stream),[])
            stop.assert_called_once_with(proc)
            self.assertTrue(proc.stdin.closed and proc.stdout.closed)
            acquired=_generation_slot.acquire(blocking=False)
            self.assertTrue(acquired)
            if acquired:_generation_slot.release()

    def test_http_response_close_signals_worker(self):
        from backend.app.coach_chat import chat_stream, Message
        stopped=threading.Event()
        def waiting(runtime,messages,cancelled):
            yield {'type':'delta','delta':'合成未完成'}
            if cancelled.wait(3):stopped.set()
        async def exercise():
            with patch('backend.app.local_codex_stream.generate_stream',side_effect=waiting):
                response=await chat_stream('qiao',Message(question='合成'))
                first=await anext(response.body_iterator)
                self.assertEqual(json.loads(first)['type'],'delta')
                await response.body_iterator.aclose()
                self.assertTrue(await asyncio.to_thread(stopped.wait,2))
        asyncio.run(exercise())

    def test_done_is_after_cleanup_and_slot_release(self):
        from backend.app.local_codex import _generation_slot
        cleaned=[]
        def events(*args):
            try:
                yield {'type':'delta','delta':'合成'}
                yield {'type':'done','answer':'合成'}
            finally:
                cleaned.append(True)
        with patch('backend.app.local_codex_stream._stream',side_effect=events):
            stream=generate_stream('unused',[])
            self.assertEqual(next(stream)['type'],'delta')
            self.assertEqual(cleaned,[])
            self.assertEqual(next(stream)['type'],'done')
            self.assertEqual(cleaned,[True])
            acquired=_generation_slot.acquire(blocking=False)
            self.assertTrue(acquired)
            if acquired:_generation_slot.release()
            stream.close()

    def run_events(self, tail, cancelled=None):
        proc = Process([{'id':1,'result':{}},{'id':2,'result':{'thread':{'id':'synthetic'}}},{'id':3,'result':{}}]+tail)
        with tempfile.TemporaryDirectory() as root, patch('backend.app.local_codex_stream.command',return_value=['codex']), patch('backend.app.local_codex_stream.subprocess.Popen',return_value=proc):
            result = list(generate_stream(root,[{'role':'system','content':'保留医学边界'},{'role':'user','content':'合成问题'}],cancelled))
        return result, proc

    def test_complete_answer_and_policy(self):
        result, proc = self.run_events([
            {'method':'item/started','params':{'item':{'id':'a','type':'agentMessage'}}},
            {'method':'item/agentMessage/delta','params':{'itemId':'a','delta':'你好'}},
            {'method':'item/completed','params':{'item':{'id':'a','type':'agentMessage','text':'你好'}}},
            {'method':'turn/completed','params':{'turn':{'status':'completed'}}}])
        self.assertEqual([e['type'] for e in result], ['delta','done'])
        sent=proc.stdin.saved.decode()
        self.assertIn('保留医学边界',sent)
        self.assertIn('"ephemeral": true',sent)
        self.assertIn('"sandbox": "read-only"',sent)

    def test_tools_and_incomplete_turn_rejected(self):
        for tail in [
            [{'method':'item/started','params':{'item':{'type':'commandExecution'}}}],
            [{'method':'turn/completed','params':{'turn':{'status':'failed'}}}],
            [{'method':'item/agentMessage/delta','params':{'itemId':'a','delta':'\ufffd'}}],
            [{'id':2,'error':{'message':'synthetic failure'}}],
        ]:
            with self.assertRaises(CodexLocalError):
                self.run_events(tail)

    def test_cancellation_and_slot_release(self):
        event=threading.Event();event.set()
        result,_=self.run_events([],event)
        self.assertEqual(result,[])
        self.test_complete_answer_and_policy()

    def test_http_stream_contract_and_error(self):
        from fastapi import FastAPI
        from backend.app.coach_chat import router
        app=FastAPI();app.include_router(router)
        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1:8765') as client:
                def success(runtime,messages,cancelled):
                    self.assertIn('不诊断',messages[0]['content'])
                    yield {'type':'delta','delta':'合成'}
                    yield {'type':'done','answer':'合成','context_version':1}
                with patch('backend.app.local_codex_stream.generate_stream',side_effect=success):
                    response=await client.post('/api/coaches/research-learning/chat/stream',json={'question':'合成问题'})
                self.assertEqual(response.status_code,200)
                self.assertEqual([json.loads(line)['type'] for line in response.text.splitlines()],['delta','done'])
                with patch('backend.app.local_codex_stream.generate_stream',side_effect=CodexLocalError('合成失败')):
                    response=await client.post('/api/coaches/research-learning/chat/stream',json={'question':'合成问题'})
                self.assertEqual(json.loads(response.text)['type'],'error')
                response=await client.post('/api/coaches/invalid/chat/stream',json={'question':'合成'})
                self.assertEqual(response.status_code,404)
        asyncio.run(exercise())

if __name__ == '__main__':
    unittest.main()
