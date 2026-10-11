"""Isolated SQLite/synthetic generation; never calls a real model."""
import asyncio
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from backend.app import book_chat


class BookHistoryRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.override = patch.object(book_chat, 'ROOT', Path(self.temp.name))
        self.override.start()
        book_chat.path_for('synthetic').write_text(json.dumps({'name': 'synthetic.txt', 'chunks': [
            {'ref': 'S1', 'location': '文本', 'text': 'Synthetic evidence.'}
        ]}), encoding='utf-8')
        with book_chat.memory_db() as db:
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,0)',
                       ('old', 'synthetic', 'assistant', 'Old synthetic answer', '[]', '2020-01-01'))

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def test_overlapping_requests_commit_only_one_complete_turn(self):
        barrier = threading.Barrier(2)
        def model(*_):
            barrier.wait(timeout=3)
            return 'Synthetic answer [S1].', {}
        def send(question):
            try:
                return asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question=question)))
            except HTTPException as error:
                return error
        with patch.object(book_chat, 'generate', side_effect=model) as generate:
            # Separate event loops/threads compete through separate SQLite connections.
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(send, ['Synthetic A', 'Synthetic B']))
        conflicts = [x for x in results if isinstance(x, HTTPException)]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].status_code, 409)
        self.assertEqual(sum(isinstance(x, dict) for x in results), 1)
        self.assertEqual(generate.call_count, 2)  # Not a model resource limiter.
        rows = book_chat.records('synthetic')
        self.assertEqual(len(rows), 3)
        self.assertEqual([r['role'] for r in rows], ['assistant', 'user', 'assistant'])
        self.assertEqual(rows[0]['content'], 'Old synthetic answer')
        # A later explicit retry reads the winning turn and can append normally.
        with patch.object(book_chat, 'generate', return_value=('Later answer [S1].', {})) as retry:
            asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Explicit retry')))
        sent = retry.call_args.args[-1]
        self.assertTrue(any(m['content'] == rows[1]['content'] for m in sent))
        self.assertEqual(len(book_chat.records('synthetic')), 5)

    def test_same_id_and_timestamp_content_edit_is_a_conflict(self):
        def model(*_):
            with book_chat.memory_db() as db:
                db.execute("UPDATE messages SET content='Synthetic updated restriction' WHERE id='old'")
            return 'Stale answer [S1].', {}
        with patch.object(book_chat, 'generate', side_effect=model):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question')))
        self.assertEqual(caught.exception.status_code, 409)
        rows = book_chat.records('synthetic')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['content'], 'Synthetic updated restriction')

    def test_bookmark_and_other_book_updates_do_not_invalidate_context(self):
        def model(*_):
            book_chat.save_message('synthetic', 'old')
            with book_chat.memory_db() as db:
                db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,0)',
                           ('other', 'another', 'user', 'Other synthetic question', '[]', '2020-01-01'))
            return 'Current answer [S1].', {}
        with patch.object(book_chat, 'generate', side_effect=model):
            result = asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question')))
        self.assertIn('id', result)
        self.assertEqual(len(book_chat.records('synthetic')), 3)
        self.assertEqual(book_chat.records('synthetic')[0]['saved'], 1)
        self.assertEqual(len(book_chat.records('another')), 1)

    def test_second_insert_failure_rolls_back_first_and_releases_lock(self):
        with book_chat.memory_db() as db:
            db.execute("CREATE TRIGGER synthetic_fail BEFORE INSERT ON messages WHEN NEW.role='assistant' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        before = book_chat.records('synthetic')
        with patch.object(book_chat, 'generate', return_value=('Synthetic answer [S1].', {})):
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Synthetic question')))
            self.assertEqual(book_chat.records('synthetic'), before)
            with book_chat.memory_db() as db:
                db.execute('DROP TRIGGER synthetic_fail')
            asyncio.run(book_chat.chat('synthetic', book_chat.Chat(question='Retry after failure')))
        self.assertEqual(len(book_chat.records('synthetic')), 3)


if __name__ == '__main__':
    unittest.main()
