"""Synthetic model and temporary database; native socket disconnect coverage."""
import asyncio
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from backend.app import book_chat


class Connection:
    def __init__(self, states):
        self.states = iter(states)

    async def is_disconnected(self):
        return next(self.states)


class BookChatDisconnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.override = patch.object(book_chat, 'ROOT', self.root)
        self.override.start()
        self.source = book_chat.path_for('synthetic')
        self.source.write_text(json.dumps({'name': 'synthetic.txt', 'chunks': [{'ref': 'S1', 'location': '文本', 'text': 'Synthetic evidence.'}]}), encoding='utf-8')
        with book_chat.memory_db() as db:
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,0)', ('old', 'synthetic', 'user', 'Old synthetic note', '[]', '2020-01-01'))
        self.before = book_chat.records('synthetic')
        self.source_bytes = self.source.read_bytes()
        self.db_bytes = (self.root / 'memory.db').read_bytes()

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def unchanged(self):
        self.assertEqual(book_chat.records('synthetic'), self.before)
        self.assertEqual((self.root / 'memory.db').read_bytes(), self.db_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_pre_generation_disconnect_does_not_call_model_or_save(self):
        for states in [[True], [False, True]]:
            with self.subTest(states=states), patch.object(book_chat, 'generate') as model:
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question'), Connection(states)))
                self.assertEqual(caught.exception.status_code, 499)
                model.assert_not_called()
                self.unchanged()

    def test_post_generation_disconnect_discards_both_turn_rows(self):
        with patch.object(book_chat, 'generate', return_value=('Synthetic answer [S1].', {})) as model:
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question'), Connection([False, False, True])))
            self.assertEqual(caught.exception.status_code, 499)
            self.assertEqual(model.call_count, 1)
            self.unchanged()

    def test_connected_http_request_still_saves_complete_turn(self):
        async def scenario():
            app = FastAPI(); app.include_router(book_chat.router)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 50000)), base_url='http://127.0.0.1') as client:
                response = await client.post('/api/books/synthetic/chat', json={'question': 'Synthetic question'})
                self.assertEqual(response.status_code, 200)
                rows = book_chat.records('synthetic')
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[0], self.before[0])
                self.assertEqual(rows[-1]['id'], response.json()['id'])
                self.assertEqual(rows[-1]['sources'][0]['document'], 'synthetic.txt')
        with patch.object(book_chat, 'generate', return_value=('Synthetic answer [S1].', {})):
            asyncio.run(scenario())

    def test_native_disconnect_during_generation_leaves_history_unchanged(self):
        entered, release, checked = threading.Event(), threading.Event(), threading.Event()
        observed = []
        original = book_chat.Request.is_disconnected
        async def observe(request):
            value = await original(request)
            observed.append(value)
            if len(observed) == 3:
                checked.set()
            return value
        def slow_model(*_):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('synthetic model wait timeout')
            return 'Synthetic answer [S1].', {}
        with patch.object(book_chat, 'generate', side_effect=slow_model), patch.object(book_chat.Request, 'is_disconnected', observe):
            app = FastAPI(); app.include_router(book_chat.router)
            listener = socket.socket(); listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, log_level='error', lifespan='off'))
            thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
            thread.start(); client = None
            try:
                deadline = time.monotonic()+5
                while not server.started and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(server.started)
                body = json.dumps({'question': 'Synthetic disconnected question'}).encode()
                client = socket.create_connection(('127.0.0.1', port), timeout=3)
                header = f'POST /api/books/synthetic/chat HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n'.encode()
                client.sendall(header+body)
                self.assertTrue(entered.wait(3))
                client.shutdown(socket.SHUT_RDWR); client.close(); client = None
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
            self.assertEqual(observed, [False, False, True])
            self.unchanged()


if __name__ == '__main__':
    unittest.main()
