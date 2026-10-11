"""Frontend handlers -> actual ASGI API -> disposable SQLite; no live server."""
import json
import os
import subprocess
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import main
from backend.test_local_boundary import with_peer


class InquiryRoundtripTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='creator-inquiry-roundtrip-')
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name)
        self.runtime_patch = patch.object(main, 'RUNTIME', self.runtime)
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.client = self.enterContext(TestClient(with_peer(main.app), base_url='http://127.0.0.1'))
        self.assertFalse(main.app.dependency_overrides, 'Do not disable local request protection')
        self.assertTrue((self.runtime / 'creator.db').is_file())

    def body(self):
        return dict(request_key=str(uuid.uuid4()), subject='合成咨询', kind='了解项目', need='合成需求')

    def test_actual_frontend_recovery_against_disposable_api(self):
        node = os.environ.get('CREATOR_TEST_NODE', 'D:/Program Files/nodejs/node.exe')
        root = Path(__file__).resolve().parents[1]
        transcript = []
        with subprocess.Popen([node, 'tests/inquiry-api-bridge.cjs', '--asgi-test-bridge'], cwd=root,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding='utf-8') as process:
            # Prevent a broken bridge hanging the test runner indefinitely.
            watchdog = threading.Timer(45, process.kill)
            watchdog.start()
            try:
                done = None
                for line in process.stdout:
                    message = json.loads(line)
                    if message.get('done'):
                        done = message
                        break
                    kwargs = {'json': message['body']} if 'body' in message else {}
                    result = self.client.request(message['method'], '/api' + message['path'], **kwargs)
                    transcript.append((message['method'], result.status_code, message.get('lost', False)))
                    reply = dict(id=message['id'], status=result.status_code, body=result.json(), lost=message.get('lost', False))
                    process.stdin.write(json.dumps(reply, ensure_ascii=False) + '\n')
                    process.stdin.flush()
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 0, process.stderr.read())
                self.assertEqual(done, dict(done=True, writes=4, rows=1, timeline=3, status='closed'))
            finally:
                watchdog.cancel()
                if process.poll() is None:
                    process.kill()
        self.assertTrue(all(status == 200 for _, status, _ in transcript))
        self.assertEqual(sum(lost for _, _, lost in transcript), 2)
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM service_requests').fetchone()[0], 1)

    def test_concurrent_duplicate_create_and_followup(self):
        body = self.body()
        with ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(lambda _: self.client.post('/api/commerce/inquiries', json=body), range(4)))
        self.assertEqual([r.status_code for r in replies], [200] * 4)
        self.assertEqual(len({r.json()['id'] for r in replies}), 1)
        rid = replies[0].json()['id']
        route = '/api/commerce/inquiries/' + rid
        with ThreadPoolExecutor(max_workers=2) as pool:
            updates = list(pool.map(lambda n: self.client.patch(route, json=dict(status='following', note=f'合成并发说明{n}', expected_version=1)), range(2)))
        self.assertEqual(sorted(r.status_code for r in updates), [200, 409])
        row = self.client.get('/api/commerce/inquiries').json()[0]
        self.assertEqual(len(row['timeline']), 2)

    def test_same_key_changed_payload_and_untrusted_origin_do_not_write(self):
        body = self.body()
        self.assertEqual(self.client.post('/api/commerce/inquiries', json=body).status_code, 200)
        for field in ['subject', 'kind', 'need']:
            self.assertEqual(self.client.post('/api/commerce/inquiries', json={**body, field: '不同合成内容'}).status_code, 409)
        self.assertEqual(self.client.post('/api/commerce/inquiries', json=self.body(), headers={'Origin': 'https://elsewhere.example'}).status_code, 403)
        rows = self.client.get('/api/commerce/inquiries').json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['timeline']), 1)


if __name__ == '__main__':
    unittest.main()
