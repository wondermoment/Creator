import asyncio
import io
import json
import subprocess
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI, UploadFile, HTTPException
import httpx
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from backend.app import book_parser as parser, book_chat

def synthetic_pdf(encrypted=False, blank=False):
    writer=PdfWriter()
    page=writer.add_blank_page(width=240,height=240)
    if not blank:
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 200 Td (Synthetic walking notes.) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
    if encrypted:writer.encrypt('synthetic-only')
    out=io.BytesIO();writer.write(out);return out.getvalue()

class BookParserTests(unittest.TestCase):
    def test_real_child_extracts_pdf_and_utf8(self):
        result=parser.parse_book_data(synthetic_pdf(),'.pdf')
        self.assertIn('Synthetic walking notes.',result[0]['text'])
        self.assertEqual(result[0]['location'],'PDF 第 1 页 · 段 1')
        text=('合成段落。'*600).encode('utf-8-sig')
        self.assertEqual(parser.parse_book_data(text,'.md'),parser.extract_chunks(text,'.md'))

    def test_actual_invalid_encrypted_and_blank_pdf(self):
        for data,code in [(b'not pdf','invalid'),(synthetic_pdf(encrypted=True),'invalid'),(synthetic_pdf(blank=True),'empty')]:
            with self.subTest(code=code),self.assertRaises(parser.BookParseError) as caught:
                parser.parse_book_data(data,'.pdf')
            self.assertEqual(caught.exception.code,code)

    def test_real_slow_child_timeout_then_slot_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'slow.py';script.write_text('import time\ntime.sleep(5)\n',encoding='utf-8')
            start=time.monotonic()
            with patch.object(parser,'WORKER_PATH',script),patch.object(parser,'PARSE_TIMEOUT',0.3):
                with self.assertRaises(parser.BookParseError) as caught:parser.parse_book_data(b'synthetic','.txt')
            self.assertEqual(caught.exception.code,'timeout')
            self.assertLess(time.monotonic()-start,3)
            self.assertEqual(parser.parse_book_data(b'next','.txt')[0]['text'],'next')

    def test_overlap_rejected_without_second_child(self):
        entered=threading.Event();release=threading.Event()
        def slow(*args,**kwargs):
            entered.set()
            if not release.wait(3):raise RuntimeError('test wait expired')
            return subprocess.CompletedProcess([],0,json.dumps({'chunks':[{'ref':'S1','location':'文本','text':'synthetic'}]}).encode())
        with patch.object(parser.subprocess,'run',side_effect=slow) as run,ThreadPoolExecutor(max_workers=1) as pool:
            first=pool.submit(parser.parse_book_data,b'synthetic','.txt')
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(parser.BookParseError) as caught:parser.parse_book_data(b'other','.txt')
                self.assertEqual(caught.exception.code,'busy');self.assertEqual(run.call_count,1)
            finally:release.set()
            self.assertEqual(first.result(timeout=3)[0]['text'],'synthetic')

    def test_malformed_worker_results_never_accepted(self):
        for payload in [b'bad json',b'[]',b'{}',b'{"chunks":[]}',b'{"chunks":[{"ref":"S999","text":"x","location":"x"}]}']:
            with patch.object(parser.subprocess,'run',return_value=subprocess.CompletedProcess([],0,payload)),self.assertRaises(parser.BookParseError) as caught:
                parser.parse_book_data(b'synthetic','.txt')
            self.assertEqual(caught.exception.code,'worker')

    def test_worker_launch_has_no_secret_environment(self):
        payload=json.dumps({'chunks':[{'ref':'S1','location':'文本','text':'synthetic'}]}).encode()
        with patch.dict(parser.os.environ,{'OPENAI_API_KEY':'synthetic-secret','CODEX_HOME':'synthetic-auth','PYTHONPATH':'synthetic-import'}),patch.object(parser.subprocess,'run',return_value=subprocess.CompletedProcess([],0,payload)) as run:
            parser.parse_book_data(b'synthetic','.txt')
        args=run.call_args.args[0];options=run.call_args.kwargs
        self.assertIn('-I',args)
        for key in ['OPENAI_API_KEY','CODEX_HOME','PYTHONPATH']:self.assertNotIn(key,options['env'])
        self.assertEqual(options['timeout'],45);self.assertEqual(options['input'],b'synthetic')

    def test_upload_failure_preserves_original_and_closes_file(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(book_chat,'ROOT',Path(directory)):
            original=book_chat.path_for('synthetic');original.write_text('{"name":"old","chunks":[]}',encoding='utf-8')
            before=original.read_bytes()
            for code in ['timeout','busy','worker']:
                file=UploadFile(file=io.BytesIO(b'synthetic'),filename='new.pdf')
                with patch.object(book_chat,'parse_book_data',side_effect=parser.BookParseError(code)),self.assertRaises(HTTPException):
                    asyncio.run(book_chat.upload('synthetic',file))
                self.assertEqual(original.read_bytes(),before);self.assertTrue(file.file.closed)

    def test_upload_does_not_block_event_loop(self):
        entered=threading.Event();release=threading.Event()
        def slow(*args):
            entered.set()
            if not release.wait(2):raise RuntimeError('event loop did not release parser')
            return [{'ref':'S1','location':'文本','text':'synthetic'}]
        async def scenario():
            file=UploadFile(file=io.BytesIO(b'synthetic'),filename='new.txt')
            task=asyncio.create_task(book_chat.upload('synthetic',file))
            try:
                for _ in range(100):
                    if entered.is_set():break
                    await asyncio.sleep(0.005)
                self.assertTrue(entered.is_set());self.assertFalse(task.done())
            finally:release.set()
            self.assertTrue((await task)['ready'])
        with tempfile.TemporaryDirectory() as directory,patch.object(book_chat,'ROOT',Path(directory)),patch.object(book_chat,'parse_book_data',side_effect=slow):
            asyncio.run(scenario())

    def test_http_upload_real_worker_and_failed_replacement(self):
        async def scenario():
            app=FastAPI();app.include_router(book_chat.router)
            transport=httpx.ASGITransport(app=app,client=('127.0.0.1',50000))
            async with httpx.AsyncClient(transport=transport,base_url='http://127.0.0.1') as client:
                uploaded=await client.post('/api/books/synthetic/source',files={'file':('sample.pdf',synthetic_pdf(),'application/pdf')})
                self.assertEqual(uploaded.status_code,200);self.assertTrue(uploaded.json()['ready'])
                before=book_chat.path_for('synthetic').read_bytes()
                self.assertIn('Synthetic walking notes.',book_chat.source('synthetic')['chunks'][0]['text'])
                failed=await client.post('/api/books/synthetic/source',files={'file':('broken.pdf',b'broken','application/pdf')})
                self.assertEqual(failed.status_code,422);self.assertEqual(book_chat.path_for('synthetic').read_bytes(),before)
                with patch.object(book_chat,'parse_book_data',side_effect=AssertionError('untrusted request reached parser')):
                    denied=await client.post('/api/books/synthetic/source',headers={'Origin':'https://elsewhere.example'},files={'file':('sample.pdf',synthetic_pdf(),'application/pdf')})
                self.assertEqual(denied.status_code,403)
        with tempfile.TemporaryDirectory() as directory,patch.object(book_chat,'ROOT',Path(directory)):
            asyncio.run(scenario())

if __name__=='__main__':unittest.main()
