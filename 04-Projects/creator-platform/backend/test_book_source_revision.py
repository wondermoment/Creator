"""Temporary source/SQLite files and synthetic generation only."""
import asyncio
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException, UploadFile
from backend.app import book_chat


class BookSourceRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.override = patch.object(book_chat, 'ROOT', self.root)
        self.override.start()
        self.path = book_chat.path_for('synthetic')
        self.old = json.dumps({'name': 'same.txt', 'chunks': [
            {'ref': 'S1', 'location': '文本', 'text': 'Old synthetic evidence.'}
        ]}).encode()
        self.path.write_bytes(self.old)
        self.before = book_chat.records('synthetic')

    def tearDown(self):
        self.override.stop(); self.temp.cleanup()

    def upload(self, book='synthetic', text=b'New synthetic evidence.'):
        return asyncio.run(book_chat.upload(book, UploadFile(file=io.BytesIO(text), filename='same.txt')))

    def send(self):
        return asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question')))

    def test_same_name_replacement_during_generation_rejects_old_answer(self):
        def generate(*_):
            self.upload()
            return 'Old synthetic answer [S1].', {}
        with patch.object(book_chat, 'generate', side_effect=generate):
            with self.assertRaises(HTTPException) as caught:
                self.send()
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn('原文资料已更新', caught.exception.detail)
        self.assertEqual(book_chat.records('synthetic'), self.before)
        self.assertEqual(book_chat.source('synthetic')['name'], 'same.txt')
        self.assertEqual(book_chat.source('synthetic')['chunks'][0]['text'], 'New synthetic evidence.')
        with patch.object(book_chat, 'generate', return_value=('New answer [S1].', {})) as generate:
            reply = self.send()
        self.assertIn('New synthetic evidence.', generate.call_args.args[-1][1]['content'])
        self.assertEqual(reply['sources'][0]['text'], 'New synthetic evidence.')
        self.assertEqual(len(book_chat.records('synthetic')), 2)

    def test_removed_or_damaged_source_rejects_answer_without_history_write(self):
        for action in ['delete', 'damage']:
            with self.subTest(action=action):
                self.path.write_bytes(self.old)
                def generate(*_):
                    if action == 'delete':
                        self.path.unlink()
                    else:
                        self.path.write_bytes(b'{synthetic damaged')
                    return 'Old answer [S1].', {}
                with patch.object(book_chat, 'generate', side_effect=generate):
                    with self.assertRaises(HTTPException) as caught:
                        self.send()
                self.assertEqual(caught.exception.status_code, 409)
                self.assertEqual(book_chat.records('synthetic'), self.before)

    def test_identical_bytes_and_other_book_change_are_not_conflicts(self):
        def generate(*_):
            self.path.write_bytes(self.old)
            self.upload('another')
            return 'Current answer [S1].', {}
        with patch.object(book_chat, 'generate', side_effect=generate):
            self.assertIn('id', self.send())
        self.assertEqual(len(book_chat.records('synthetic')), 2)

    def test_upload_waits_for_shared_database_commit_lock(self):
        attempted, replaced = threading.Event(), threading.Event()
        real_connect, real_replace = book_chat.sqlite3.connect, Path.replace
        def connect(*args, **kwargs):
            db = real_connect(*args, **kwargs)
            db.set_trace_callback(lambda sql: attempted.set() if sql == 'BEGIN IMMEDIATE' else None)
            return db
        def replace(path, target):
            replaced.set()
            return real_replace(path, target)
        lock = real_connect(self.root / 'memory.db')
        lock.execute('BEGIN IMMEDIATE')
        try:
            with patch.object(book_chat.sqlite3, 'connect', side_effect=connect), patch.object(Path, 'replace', replace), ThreadPoolExecutor(max_workers=1) as pool:
                task = pool.submit(self.upload)
                try:
                    self.assertTrue(attempted.wait(3))
                    self.assertFalse(replaced.is_set())
                    self.assertEqual(self.path.read_bytes(), self.old)
                finally:
                    lock.rollback()
                self.assertTrue(task.result(timeout=3)['ready'])
                self.assertTrue(replaced.is_set())
        finally:
            lock.close()
        self.assertEqual(list(self.root.glob('*.tmp')), [])

    def test_replace_failure_preserves_source_and_releases_shared_lock(self):
        with patch.object(Path, 'replace', side_effect=OSError('synthetic replace failure')):
            with self.assertRaises(OSError):
                self.upload()
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertEqual(list(self.root.glob('*.tmp')), [])
        self.assertTrue(self.upload()['ready'])


if __name__ == '__main__':
    unittest.main()
