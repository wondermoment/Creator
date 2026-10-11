import os
import tempfile
import unittest
from datetime import datetime, timezone

_runtime = tempfile.TemporaryDirectory()
os.environ['CREATOR_RUNTIME'] = _runtime.name
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import main
from backend.test_local_boundary import with_peer


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.old_runtime = main.RUNTIME
        self.runtime = tempfile.TemporaryDirectory()
        from pathlib import Path
        main.RUNTIME = Path(self.runtime.name)

    def tearDown(self):
        main.RUNTIME = self.old_runtime
        self.runtime.cleanup()

    def test_closed_loop_and_validation(self):
        with TestClient(with_peer(app), base_url="http://127.0.0.1") as c:
            self.assertEqual(c.get('/').status_code, 200)
            self.assertEqual(len(c.get('/api/overview').json()['patients']), 3)
            body = {'metric': 'weight', 'value': 66.3, 'source': '体脂秤', 'observed_at': datetime.now(timezone.utc).isoformat()}
            self.assertEqual(c.post('/api/patients/missing/observations', json=body).status_code, 404)
            self.assertEqual(c.post('/api/patients/p1/observations', json={**body, 'value': -1}).status_code, 422)
            self.assertEqual(c.post('/api/patients/p1/observations', json=body).status_code, 201)
            proposal = c.post('/api/patients/p1/review').json()
            self.assertTrue(proposal['created'])
            self.assertFalse(c.post('/api/patients/p1/review').json()['created'])
            decision = {'decision': 'approved', 'reason': '已核对设备读数，安排客户复盘'}
            endpoint = f"/api/recommendations/{proposal['id']}/decision"
            self.assertEqual(c.post(endpoint, json={**decision, 'reason': '  '}).status_code, 422)
            self.assertEqual(c.post(endpoint, json=decision).status_code, 200)
            self.assertEqual(c.post(endpoint, json=decision).status_code, 409)
            tasks = c.get('/api/overview').json()['tasks']
            self.assertEqual(len(tasks), 1)
            endpoint = f"/api/tasks/{tasks[0]['id']}/complete"
            self.assertEqual(c.post(endpoint, json={'review': '客户已确认测量条件，下周继续观察'}).status_code, 200)
            self.assertEqual(c.post(endpoint, json={'review': '再次完成'}).status_code, 409)
            self.assertEqual(c.post('/api/recommendations/r2/decision', json={'decision': 'rejected', 'reason': '需要更多测量数据'}).status_code, 200)
            self.assertEqual(len(c.get('/api/overview').json()['tasks']), 1)
            self.assertEqual(c.post('/api/patients/p1/reports', files={'file': ('bad.pdf', b'not-pdf')}).status_code, 422)
            data = b'%PDF-1.4\n%%EOF'
            r = c.post('/api/patients/p1/reports', files={'file': ('demo.pdf', data, 'application/pdf')})
            self.assertEqual(r.status_code, 201)
            self.assertEqual(c.get('/api/reports/' + r.json()['id']).content, data)
            detail = c.get('/api/patients/p1').json()
            self.assertTrue(any(e['kind'] == 'task.completed' for e in detail['events']))
        with TestClient(with_peer(app), base_url="http://127.0.0.1") as c:
            self.assertEqual(len(c.get('/api/overview').json()['tasks']), 1)


if __name__ == '__main__':
    unittest.main()
