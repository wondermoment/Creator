"""Synthetic uploads/temp sources only; includes native loopback disconnect."""
import asyncio
import io
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI, HTTPException, UploadFile
import uvicorn
from backend.app import book_chat

CHUNKS = [{'ref': 'S1', 'location': '文本', 'text': 'synthetic replacement'}]
OLD = '{"name":"synthetic-old.txt","chunks":[{"ref":"S1","location":"文本","text":"old synthetic"}]}'


class Connection:
    def __init__(self, states):
        self.states = iter(states)

    async def is_disconnected(self):
        return next(self.states)


class UploadDisconnectTests(unittest.TestCase):
    def test_disconnected_before_parse_preserves_source_and_closes_upload(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(book_chat, 'ROOT', Path(directory)):
            p = book_chat.path_for('synthetic'); p.write_text(OLD, encoding='utf-8')
            upload = UploadFile(file=io.BytesIO(b'synthetic'), filename='new.txt')
            with patch.object(book_chat, 'parse_book_data') as parse, self.assertRaises(HTTPException) as caught:
                asyncio.run(book_chat.upload('synthetic', upload, Connection([True])))
            self.assertEqual(caught.exception.status_code, 499); parse.assert_not_called()
            self.assertTrue(upload.file.closed); self.assertEqual(p.read_text('utf-8'), OLD)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_disconnect_after_parse_discards_result_but_connected_can_replace(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(book_chat, 'ROOT', Path(directory)):
            p = book_chat.path_for('synthetic'); p.write_text(OLD, encoding='utf-8')
            with patch.object(book_chat, 'parse_book_data', return_value=CHUNKS) as parse:
                upload = UploadFile(file=io.BytesIO(b'synthetic'), filename='new.txt')
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(book_chat.upload('synthetic', upload, Connection([False, True])))
                self.assertEqual(caught.exception.status_code, 499); self.assertEqual(parse.call_count, 1)
                self.assertEqual(p.read_text('utf-8'), OLD); self.assertEqual(list(Path(directory).glob('*.tmp')), [])
                upload = UploadFile(file=io.BytesIO(b'synthetic'), filename='new.txt')
                result = asyncio.run(book_chat.upload('synthetic', upload, Connection([False, False])))
                self.assertTrue(result['ready']); self.assertEqual(book_chat.source('synthetic')['chunks'], CHUNKS)

    def test_native_socket_disconnect_during_parse_does_not_commit(self):
        entered, release, checked = threading.Event(), threading.Event(), threading.Event()
        observed = []
        original_check = book_chat.Request.is_disconnected

        async def observe(request):
            value = await original_check(request)
            observed.append(value)
            if len(observed) == 2:
                checked.set()
            return value

        def slow_parser(*_):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('fixture parser release timeout')
            return CHUNKS

        with tempfile.TemporaryDirectory() as directory, patch.object(book_chat, 'ROOT', Path(directory)), patch.object(book_chat, 'parse_book_data', side_effect=slow_parser), patch.object(book_chat.Request, 'is_disconnected', observe):
            path = book_chat.path_for('synthetic'); path.write_text(OLD, encoding='utf-8')
            app = FastAPI(); app.include_router(book_chat.router)
            listener = socket.socket(); listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='error', lifespan='off'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
            thread.start()
            client = None
            try:
                deadline = time.monotonic()+5
                while not server.started and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(server.started)
                body = b'--synthetic-boundary\r\nContent-Disposition: form-data; name="file"; filename="new.txt"\r\nContent-Type: text/plain\r\n\r\nSynthetic data only.\r\n--synthetic-boundary--\r\n'
                client = socket.create_connection(('127.0.0.1', port), timeout=3)
                header = f'POST /api/books/synthetic/source HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: multipart/form-data; boundary=synthetic-boundary\r\nContent-Length: {len(body)}\r\n\r\n'.encode()
                client.sendall(header+body)
                self.assertTrue(entered.wait(3))
                client.shutdown(socket.SHUT_RDWR); client.close(); client = None
                # Wait for uvicorn's connection set to record the real socket loss.
                deadline = time.monotonic()+3
                while server.server_state.connections and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertFalse(server.server_state.connections)
                release.set(); self.assertTrue(checked.wait(3))
            finally:
                if client is not None:
                    client.close()
                release.set(); server.should_exit = True; thread.join(timeout=5); listener.close()
            self.assertFalse(thread.is_alive())
            self.assertEqual(observed, [False, True])
            self.assertEqual(path.read_text('utf-8'), OLD)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
