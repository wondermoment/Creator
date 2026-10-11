import hashlib
import unittest

from test_creation_tools import CreationToolsTests, server


class ProvenanceDeliveryTests(unittest.TestCase):
    setUp = CreationToolsTests.setUp
    configure = CreationToolsTests.configure
    job = CreationToolsTests.job
    complete = CreationToolsTests.complete
    repurpose_with_reference_parent = CreationToolsTests.repurpose_with_reference_parent
    change_parent_reference = CreationToolsTests.change_parent_reference

    def draft(self):
        _, reference, payload = self.repurpose_with_reference_parent()
        jid = self.job(**payload)
        self.complete(jid, {'answer': '模拟口播：先确认采购条件。[1]', 'model': 'mock'})
        response = self.a.post(self.url+'/repurpose/from-job/'+jid, json={})
        self.assertEqual(response.status_code, 200, response.text)
        cid = response.json()['id']
        with server.db() as c:
            content = server.resource(c, self.pid, cid, 'content')
            content['channels'] = ['企业官网']
            content['layout'] = {'body_sha256': hashlib.sha256(content['body'].encode()).hexdigest(),
                                 'blocks': [{'text': content['body']}], 'figures': []}
            server.put(c, self.pid, 'content', content, cid)
        return cid, reference

    def review(self, cid, action):
        return self.a.post(self.url+'/contents/'+cid+'/review', json={'revision': 1, 'action': action})

    def test_stale_parent_blocks_submit_and_approval(self):
        cid, ref = self.draft()
        self.change_parent_reference(ref)
        self.assertEqual(self.review(cid, 'submit').status_code, 409)
        with server.db() as c:
            content = server.resource(c, self.pid, cid, 'content')
            content['status'] = 'pending'
            server.put(c, self.pid, 'content', content, cid)
        self.assertEqual(self.review(cid, 'approve').status_code, 409)

    def test_manuscript_edit_history_is_not_untraced_chat_history(self):
        cid, _, payload = self.repurpose_with_reference_parent()
        with server.db() as c:
            parent = server.resource(c, self.pid, cid, 'content')
            parent['history'] = [{'revision': 1, 'body': '先前手工编辑版本'}]
            parent['revision'] = 2
            server.put(c, self.pid, 'content', parent, cid)
        jid = self.job(**payload)
        self.complete(jid, {'answer': '基于已编辑原稿的模拟内容', 'model': 'mock'})
        self.assertEqual(self.a.post(self.url+'/repurpose/from-job/'+jid, json={}).status_code, 200)

    def test_stale_parent_revokes_effective_approval_and_delivery(self):
        cid, ref = self.draft()
        for action in ('submit', 'approve'):
            self.assertEqual(self.review(cid, action).status_code, 200)
        base = self.url+'/contents/'+cid
        self.assertEqual(self.a.get(base+'/package').status_code, 200)
        publication = self.a.post(base+'/publish', json={'revision': 1}).json()['ids'][0]
        self.change_parent_reference(ref)
        state = self.a.get(self.url+'/state').json()
        content = next(x for x in state['content'] if x['id'] == cid)
        self.assertFalse(content['approval_summary']['effective_approved'])
        self.assertTrue(content['approval_summary']['sources_outdated'])
        self.assertEqual(content['status'], 'approved')  # Historical approval remains intact.
        self.assertEqual(self.a.get(base+'/package').status_code, 409)
        self.assertEqual(self.a.post(base+'/publish', json={'revision': 1}).status_code, 409)
        self.assertEqual(self.a.post(self.url+'/publications/'+publication+'/receipt',
                                    json={'url': 'https://example.com/post'}).status_code, 409)

    def test_stale_parent_blocks_portable_preview_but_keeps_internal_proof(self):
        cid, ref = self.draft()
        base = self.url+'/contents/'+cid
        self.assertEqual(self.a.get(base+'/client-preview?revision=1').status_code, 200)
        for action in ('submit', 'approve'):
            self.assertEqual(self.review(cid, action).status_code, 200)
        self.change_parent_reference(ref)
        for suffix in ('', '&download=true', '&format=png'):
            self.assertEqual(self.a.get(base+'/client-preview?revision=1'+suffix).status_code, 409)
        proof = self.a.get(base+'/proof?revision=1')
        self.assertEqual(proof.status_code, 200)
        self.assertNotIn('当前版本已审核', proof.text)
        self.assertIn('依据待核验', proof.text)
        self.assertEqual(self.b.get(base+'/proof?revision=1').status_code, 404)


if __name__ == '__main__':
    unittest.main()
