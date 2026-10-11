import unittest
import test_workflow as workflow
server=workflow.server

class IntentTests(unittest.TestCase):
    setUp=workflow.WorkflowTests.setUp
    def test_imported_intent_edit_isolated_versioned_and_preserves_source(self):
        original={'title':'选题','tag':'选型','question':'怎么选','strategy':'核对条件','cta':'咨询','version':1,'source_file':'用户意图.xlsx','source_sheet':'用户意图','source_cell':'B2:G2','source_original':{'title':'原始选题'},'group':'L1'}
        with server.db() as c: rid=server.put(c,self.pid,'user_intent',original)
        path=self.url+'/user-intents/'+rid
        body={k:original[k] for k in ['title','tag','question','strategy','cta','version']};body['title']='修改后的选题'
        self.assertEqual(self.b.put(path,json=body).status_code,404)
        self.assertEqual(self.a.put(path,json={**body,'title':'  '}).status_code,422)
        self.assertEqual(self.a.put(path,json=body).status_code,200)
        self.assertEqual(self.a.put(path,json=body).status_code,409)
        record=next(x for x in self.a.get(self.url+'/state').json()['user_intent'] if x['id']==rid)
        self.assertEqual(record['version'],2);self.assertEqual(record['history'][0]['title'],'选题')
        self.assertEqual(record['source_original'],original['source_original']);self.assertEqual(record['source_cell'],'B2:G2')
        self.assertEqual(self.b.get(self.url+'/state').status_code,404)
        identity=self.b.get('/api/me').json()['identity']
        self.a.post(self.url+'/members',json={'identity':identity,'role':'viewer'})
        self.assertEqual(self.b.put(path,json={**body,'version':2}).status_code,403)

    def test_overview_single_knowledge_version_and_access(self):
        with server.db() as c:
            kid=server.put(c,self.pid,'knowledge',{'title':'综合概述','body':'原始正文','version':1,'status':'pending','category':'品牌档案','source':'原始文档'})
            server.put(c,self.pid,'brand',{'version':1,'overview_knowledge_id':kid,'positioning':'保持定位'})
        path=self.url+'/brand/overview'
        self.assertEqual(self.b.put(path,json={'value':'新概述','version':1}).status_code,404)
        self.assertEqual(self.a.put(path,json={'value':'新概述','version':1}).status_code,200)
        self.assertEqual(self.a.put(path,json={'value':'旧版本','version':1}).status_code,409)
        self.assertEqual(self.a.put(path,json={'value':'  ','version':2}).status_code,422)
        with server.db() as c:
            doc=server.resource(c,self.pid,kid,'knowledge');self.assertEqual(doc['version'],2)
            self.assertEqual(doc['history'][0]['body'],'原始正文');self.assertEqual(doc['status'],'pending')
            self.assertEqual(server.items(c,self.pid,'brand')[0]['positioning'],'保持定位')

if __name__=='__main__':unittest.main()
