import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

TMP = tempfile.TemporaryDirectory()
os.environ['GEO_DB_PATH'] = str(Path(TMP.name) / 'test.db')
from fastapi.testclient import TestClient
import server


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        # Each fixture gets a fresh rate-limit window, without disabling the actual middleware.
        with server.db() as c:
            c.execute('DELETE FROM auth_limits')
        self.a = TestClient(server.app)
        self.b = TestClient(server.app)
        for client in (self.a, self.b):
            r = client.post('/api/demo')
            self.assertEqual(r.status_code, 200, r.text)
            client.headers['x-csrf-token'] = r.json()['csrf']
        self.pid = self.a.get('/api/me').json()['projects'][0]['id']
        # Demo projects are ordered by random ids if created in the same second.
        self.pid = next(p['id'] for p in self.a.get('/api/me').json()['projects'] if '澄川' in p['name'])
        self.url = '/api/projects/' + self.pid
        # Legacy configuration tests run as an explicitly authorized technical operator.
        with server.db() as c:
            actor=c.execute('SELECT user_id FROM members WHERE project_id=? AND role="owner"',(self.pid,)).fetchone()[0]
        import json
        path=server.DB_PATH.parent/'prompt-admins.json'
        allowed=json.loads(path.read_text()) if path.exists() else []
        path.write_text(json.dumps(allowed+[actor]))
        self.state = self.a.get(self.url + '/state').json()
        self.kid = self.state['knowledge'][0]['id']

    def task(self, **overrides):
        payload = {'name': '每周知识内容', 'task_type': 'content', 'frequency': 'weekly', 'start_at': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(), 'title': '如何明确材料要求？', 'skill_id': 'faq', 'knowledge_ids': [self.kid], 'channels': ['知乎'], 'submit_review': True}
        payload.update(overrides)
        r = self.a.post(self.url+'/automations', json=payload)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['id']

    def test_isolation_and_csrf(self):
        self.assertEqual(self.b.get(self.url+'/state').status_code, 404)
        self.assertEqual(self.b.post(self.url+'/knowledge-search', json={'query':'图纸'}).status_code,404)
        r = self.a.post(self.url+'/brand', json={'voice':'专业克制'},headers={'x-csrf-token':'bad'})
        self.assertEqual(r.status_code,403)
        tid=self.task()
        self.assertEqual(self.b.post(self.url+'/automations/'+tid+'/action',json={'action':'run'}).status_code,404)

    def test_brand_intent_and_review_gate(self):
        self.a.post(self.url+'/brand',json={'voice':'克制、具体','forbidden':'不使用保证通过'})
        r=self.a.post(self.url+'/generate',json={'title':'采购材料选型','skill_id':'faq','knowledge_ids':[self.kid],'channels':['知乎'],'keyword':'材料','intent':'采购选型','customer_question':'材料如何确认？','prompt_override':'先明确条件，再给采购建议。'})
        self.assertEqual(r.status_code,200,r.text)
        rid=r.json()['id']
        content=next(x for x in self.a.get(self.url+'/state').json()['content'] if x['id']==rid)
        self.assertIn('克制、具体',content['prompt_snapshot'])
        self.assertEqual(content['keyword'],'材料')
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).status_code,409)
        self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':'submit'})
        self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':'approve'})
        one=self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).json()
        two=self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).json()
        self.assertEqual(len(one['ids']),1)
        self.assertEqual(two['ids'],[])
        self.a.put(self.url+'/contents/'+rid,json={'revision':1,'title':'新标题','body':'新的内容','channels':['知乎']})
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).status_code,409)
        pub=next(x for x in self.a.get(self.url+'/state').json()['publication'] if x['id']==one['ids'][0])
        self.assertEqual(pub['status'],'cancelled')

    def test_scheduler_once_idempotency_pause_and_restart_cursor(self):
        tid=self.task(frequency='once')
        before=len(self.a.get(self.url+'/state').json()['content'])
        stamp=datetime.now(timezone.utc)+timedelta(hours=2)
        server.scheduler_tick(stamp)
        server.scheduler_tick(stamp)
        s=self.a.get(self.url+'/state').json()
        self.assertEqual(len(s['content']),before+1)
        t=next(x for x in s['automation'] if x['id']==tid)
        self.assertEqual(t['status'],'completed')
        self.assertEqual(t['run_count'],1)
        created=next(x for x in s['content'] if x.get('automation_id')==tid)
        self.assertEqual(created['status'],'pending')
        self.assertIsNone(created['approved_revision'])
        weekly=self.task()
        self.a.post(self.url+'/automations/'+weekly+'/action',json={'action':'pause'})
        server.scheduler_tick(stamp+timedelta(days=20))
        t=next(x for x in self.a.get(self.url+'/state').json()['automation'] if x['id']==weekly)
        self.assertEqual(t['run_count'],0)
        self.a.post(self.url+'/automations/'+weekly+'/action',json={'action':'resume'})
        server.scheduler_tick(stamp+timedelta(days=20))
        t=next(x for x in self.a.get(self.url+'/state').json()['automation'] if x['id']==weekly)
        self.assertEqual(t['run_count'],1)
        self.assertGreater(datetime.fromisoformat(t['next_run']),stamp+timedelta(days=20))

    def test_failure_does_not_generate_partial_content(self):
        tid=self.task()
        with server.db() as c:
            item=server.resource(c,self.pid,self.kid,'knowledge')
            item['status']='pending'
            server.put(c,self.pid,'knowledge',item,self.kid)
        server.scheduler_tick(datetime.now(timezone.utc)+timedelta(hours=2))
        s=self.a.get(self.url+'/state').json()
        task=next(x for x in s['automation'] if x['id']==tid)
        self.assertEqual(task['status'],'failed')
        self.assertFalse(any(x.get('automation_id')==tid for x in s['content']))

    def test_knowledge_faq_asset_permissions(self):
        self.assertTrue(self.a.post(self.url+'/knowledge-search',json={'query':'图纸'}).json()['matches'])
        self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'zzzxqv987unlikely'}).json()['matches'])
        r=self.a.post(self.url+'/faq',json={'question':'需要准备什么？','answer':'准备图纸与材料要求。','source_ids':[self.kid]})
        self.assertEqual(r.status_code,200,r.text)
        faq=self.a.get(self.url+'/state').json()['faq'][0]
        k=next(x for x in self.a.get(self.url+'/state').json()['knowledge'] if x['id']==faq['knowledge_id'])
        self.assertEqual(k['status'],'pending')
        r=self.a.post(self.url+'/assets?filename=brand.pdf',content=b'%PDF-1.7\nlocal test document',headers={'content-type':'application/octet-stream'})
        self.assertEqual(r.status_code,200,r.text)
        asset_path=self.url+'/assets/'+r.json()['id']+'/file'
        self.assertEqual(self.a.get(asset_path).status_code,200)
        self.assertEqual(self.b.get(asset_path).status_code,404)
        self.assertEqual(self.a.post(self.url+'/assets?filename=bad.png',content=b'<script>bad</script>').status_code,422)

    def test_manager_task_idempotency_and_tenant_scope(self):
        self.assertEqual(self.b.get(self.url+'/manager').status_code,404)
        r=self.a.post(self.url+'/manager/chat',json={'text':'安排一篇产品选型文章','intent':'task','request_id':'test-request-01'})
        self.assertEqual(r.status_code,200,r.text)
        message=r.json()
        repeated=self.a.post(self.url+'/manager/chat',json={'text':'安排一篇产品选型文章','intent':'task','request_id':'test-request-01'}).json()
        self.assertEqual(message['id'],repeated['id'])
        payload={**message['proposal'],'message_id':message['id']}
        task=self.a.post(self.url+'/manager/tasks',json=payload)
        self.assertEqual(task.status_code,200,task.text)
        rid=task.json()['id']
        self.assertEqual(self.a.post(self.url+'/manager/tasks',json=payload).json()['id'],rid)
        self.assertEqual(self.b.put(self.url+'/manager/tasks/'+rid,json={'status':'done','result':'完成','revision':1}).status_code,404)
        self.assertEqual(self.a.put(self.url+'/manager/tasks/'+rid,json={'status':'done','result':'','revision':1}).status_code,422)
        self.assertEqual(self.a.put(self.url+'/manager/tasks/'+rid,json={'status':'done','result':'已交付文章文档','revision':1}).status_code,200)
        self.assertEqual(self.a.put(self.url+'/manager/tasks/'+rid,json={'status':'doing','revision':1}).status_code,409)
        ctx=self.a.get(self.url+'/manager').json()['context']
        self.assertEqual(ctx['task_count'],1)
        self.assertEqual(ctx['task_done'],1)

    def test_soul_customization_and_expert_snapshot(self):
        before=self.a.get(self.url+'/manager').json()['agents']
        expert=next(a for a in before if a['agent_id']=='technical')
        md=expert['markdown']+'\n企业专属语气：先说明测试条件。'
        result=self.a.put(self.url+'/agents/technical/soul',json={'markdown':md,'version':1})
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue((server.DB_PATH.parent/'agents'/self.pid/'technical'/'soul.md').exists())
        self.assertEqual(self.a.put(self.url+'/agents/technical/soul',json={'markdown':md,'version':1}).status_code,409)
        self.assertEqual(self.b.get(self.url+'/agents/technical/soul.md').status_code,404)
        generated=self.a.post(self.url+'/generate',json={'title':'技术使用条件','skill_id':'product','knowledge_ids':[self.kid],'channels':['企业官网'],'expert_id':'technical'})
        self.assertEqual(generated.status_code,200,generated.text)
        content=next(x for x in self.a.get(self.url+'/state').json()['content'] if x['id']==generated.json()['id'])
        self.assertEqual(content['soul_version'],2)
        self.assertIn('企业专属语气',content['prompt_snapshot'])
        self.assertEqual(content['expert_id'],'technical')

    def test_comments_dedup_conversion_and_followup(self):
        entry=self.a.post(self.url+'/contact-entries',json={'name':'官网企业微信','method':'企业微信','value':'客服','url':'https://example.com/contact','placement':'官网'}).json()['id']
        comment={'platform':'知乎','text':'请提供产品选型资料','author':'咨询者','external_id':'abc123','contact':''}
        imported=self.a.post(self.url+'/comments/import',json={'comments':[comment,comment]}).json()
        self.assertEqual(len(imported['ids']),1)
        self.assertEqual(imported['skipped'],1)
        self.assertEqual(self.b.post(self.url+'/comments/'+imported['ids'][0]+'/action',json={'action':'convert'}).status_code,404)
        first=self.a.post(self.url+'/comments/'+imported['ids'][0]+'/action',json={'action':'convert'}).json()
        second=self.a.post(self.url+'/comments/'+imported['ids'][0]+'/action',json={'action':'convert'}).json()
        self.assertEqual(first['lead_id'],second['lead_id'])
        rid=first['lead_id']
        lead=next(l for l in self.a.get(self.url+'/state').json()['lead'] if l['id']==rid)
        self.assertEqual(lead['status'],'new')
        result=self.a.put(self.url+'/leads/'+rid,json={'status':'contacted','owner':'接待人员','note':'等待图纸','revision':1,'next_followup':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
        self.assertEqual(result.status_code,200,result.text)
        lead=next(l for l in self.a.get(self.url+'/state').json()['lead'] if l['id']==rid)
        self.assertEqual(lead['history'][0]['note'],'等待图纸')
        self.assertEqual(lead['revision'],2)

    def test_password_login_session_and_reload(self):
        client=TestClient(server.app)
        identity='login-'+server.uid()+'@example.com'
        payload={'identity':identity,'password':'local-test-password-123'}
        r=client.post('/api/register',json=payload)
        self.assertEqual(r.status_code,200,r.text)
        client.cookies.clear()
        self.assertEqual(client.get('/api/me').status_code,401)
        self.assertEqual(client.post('/api/login',json={**payload,'password':'incorrect-test-pass'}).status_code,401)
        self.assertEqual(client.post('/api/login',json=payload).status_code,200)
        self.assertEqual(client.get('/api/me').json()['identity'],identity)
        self.assertEqual(client.get('/api/me').status_code,200)


if __name__=='__main__':
    unittest.main()
