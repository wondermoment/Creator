import unittest
import test_workflow as workflow
server=workflow.server

class QaWorkbenchTests(unittest.TestCase):
    setUp=workflow.WorkflowTests.setUp

    def create_answer(self):
        r=self.a.post(self.url+'/faq',json={'question':'设备如何选型？','answer':'核对图纸与材料要求。','category':'采购选型','source_ids':[self.kid],'source_versions':{self.kid:1}})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()['id']

    def test_edit_keeps_provenance_and_invalidates_old_confirmation(self):
        rid=self.create_answer()
        with server.db() as c:
            faq=server.resource(c,self.pid,rid,'faq');kid=faq['knowledge_id']
        self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':1}).status_code,200)
        edit={'question':'采购设备如何选型？','answer':'先核对最新图纸、材料与验收要求。','category':'采购选型','version':1}
        self.assertEqual(self.a.put(self.url+'/faq/'+rid,json=edit).status_code,200)
        self.assertEqual(self.a.put(self.url+'/faq/'+rid,json=edit).status_code,409)
        self.assertEqual(self.a.put(self.url+'/faq/'+rid,json={**edit,'version':2,'answer':'  '}).status_code,422)
        self.assertEqual(self.b.put(self.url+'/faq/'+rid,json={**edit,'version':2}).status_code,404)
        with server.db() as c:
            f=server.resource(c,self.pid,rid,'faq');k=server.resource(c,self.pid,kid,'knowledge')
            self.assertEqual(k['version'],2);self.assertEqual(k['status'],'pending')
            self.assertNotIn('confirmed_at',k)
            self.assertEqual(k['history'][0]['body'],'核对图纸与材料要求。')
            self.assertEqual(f['history'][0]['question'],'设备如何选型？')
            self.assertEqual(f['source_snapshots'],faq['source_snapshots'])
            self.assertEqual(k['body'],f['answer']);self.assertEqual(k['title'],f['question'])
            self.assertFalse(server.knowledge_review_summary(c,self.pid,k)['effective_confirmed'])
            actor=c.execute("SELECT user_id FROM members WHERE project_id=? AND role='owner'",(self.pid,)).fetchone()[0]
            c.execute("UPDATE members SET role='viewer' WHERE project_id=? AND user_id=?",(self.pid,actor))
        self.assertEqual(self.a.put(self.url+'/faq/'+rid,json={**edit,'version':2}).status_code,403)

    def test_link_question_requires_same_enterprise_and_keeps_original(self):
        with server.db() as c:origin=server.put(c,self.pid,'insight',{'question':'怎样选型？','title':'选型','platform':'销售沟通'})
        payload={'question':'怎样选型？','answer':'核对图纸。','origin_kind':'insight','origin_id':origin}
        r=self.a.post(self.url+'/faq',json=payload);self.assertEqual(r.status_code,200,r.text)
        other=self.b.get('/api/me').json()['projects'][0]['id']
        self.assertEqual(self.b.post('/api/projects/'+other+'/faq',json=payload).status_code,404)
        self.assertEqual(self.a.post(self.url+'/faq',json={**payload,'origin_kind':'knowledge'}).status_code,422)
        self.assertEqual(self.a.post(self.url+'/faq',json={**payload,'question':'  '}).status_code,422)
        with server.db() as c:
            self.assertEqual(server.resource(c,self.pid,origin,'insight')['question'],'怎样选型？')
            self.assertEqual(server.resource(c,self.pid,r.json()['id'],'faq')['origin_id'],origin)

    def test_edit_does_not_rebase_changed_sources(self):
        rid=self.create_answer()
        with server.db() as c:
            source=server.resource(c,self.pid,self.kid,'knowledge');source['version']=2;server.put(c,self.pid,'knowledge',source,self.kid)
        r=self.a.put(self.url+'/faq/'+rid,json={'question':'如何选型？','answer':'修改草稿。','category':'产品问答','version':1})
        self.assertEqual(r.status_code,200)
        with server.db() as c:
            f=server.resource(c,self.pid,rid,'faq');k=server.resource(c,self.pid,f['knowledge_id'],'knowledge')
            self.assertEqual(f['source_snapshots'][0]['version'],1)
            self.assertFalse(server.knowledge_usable(c,self.pid,k,require_confirmed=False))

if __name__=='__main__':unittest.main()
