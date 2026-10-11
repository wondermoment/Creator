import io
import json
import unittest
from unittest.mock import patch
import test_workflow as workflow
import delivery_runtime as runtime

server = workflow.server


class DeliveryTests(unittest.TestCase):
    setUp = workflow.WorkflowTests.setUp

    def configure(self, kind='model'):
        r = self.a.post(self.url + '/execution/connectors', json={'kind': kind, 'endpoint': 'https://example.com/v1' if kind == 'model' else 'https://example.com',
            'model': 'test-model', 'username': 'publisher', 'secret': 'private-test-secret', 'input_price': 2, 'output_price': 4})
        self.assertEqual(r.status_code, 200, r.text)

    def tick_job(self, jid):
        # Run just this fixture's job, rather than any unrelated queued fixture.
        with server.db() as c:
            job = server.resource(c, self.pid, jid, 'execution')
        return server.delivery['perform'](self.pid, job)

    def generate(self, real=False):
        r = self.a.post(self.url + ('/execution/generate' if real else '/generate'), json={'title': '采购资料说明', 'skill_id': 'faq', 'knowledge_ids': [self.kid], 'channels': ['企业官网', '知乎']})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_secrets_roles_and_tenant_isolation(self):
        self.configure()
        text = self.a.get(self.url + '/execution').text + self.a.get(self.url + '/state').text
        self.assertNotIn('private-test-secret', text)
        self.assertNotIn('encrypted_secret', text)
        self.assertEqual(self.b.get(self.url + '/execution').status_code, 404)
        self.assertEqual(self.b.post(self.url + '/execution/jobs', json={'kind': 'model_test'}).status_code, 404)
        with server.db() as c:
            record = server.items(c, self.pid, 'connector')[0]
            self.assertNotIn('private-test-secret', record['encrypted_secret'])
        user = self.b.get('/api/me').json()['identity']
        self.a.post(self.url + '/members', json={'identity': user, 'role': 'reviewer'})
        self.assertEqual(self.b.post(self.url + '/execution/connectors', json={'kind': 'model', 'endpoint': 'https://example.com'}).status_code, 403)
        self.assertEqual(self.b.post(self.url + '/execution/jobs', json={'kind': 'model_test'}).status_code, 403)

    def test_local_codex_uses_selected_tenant_sources_and_no_api_secret(self):
        config = {'kind': 'model', 'transport': 'codex_local', 'model': 'gpt-6-sol'}
        with patch.object(runtime.codex_local, 'availability', return_value={'available': False, 'reason': 'not authorized'}):
            self.assertEqual(self.a.post(self.url+'/execution/connectors', json=config).status_code, 409)
        with patch.object(runtime.codex_local, 'availability', return_value={'available': True, 'reason': 'ready'}):
            self.assertEqual(self.b.post(self.url+'/execution/connectors', json=config).status_code, 404)
            self.assertEqual(self.a.post(self.url+'/execution/connectors', json=config).status_code, 200)
            connector = next(c for c in self.a.get(self.url+'/execution').json()['connectors'] if c['provider']=='model')
            self.assertTrue(connector['ready'])
            self.assertFalse(connector['has_secret'])
            self.assertEqual(self.a.post(self.url+'/execution/jobs', json={'kind':'geo_api','question':'suppliers?'}).status_code,409)
            test = self.a.post(self.url+'/execution/jobs', json={'kind':'model_test'})
            self.assertEqual(test.status_code,200,test.text)
            data = self.generate(True)
            with patch.object(runtime,'request_json') as api, patch.object(runtime.codex_local,'generate',return_value=('正文 [1]',{'transport':'codex_local','usage':{'prompt_tokens':12},'estimated_cost':None})) as generate:
                self.tick_job(test.json()['id'])
                self.tick_job(data['job_id'])
                api.assert_not_called()
                args = generate.call_args.args
                self.assertEqual(args[1],self.pid)
                self.assertIn('知识资料',args[3][1]['content'])
            content = next(c for c in self.a.get(self.url+'/state').json()['content'] if c['id']==data['id'])
            self.assertEqual(content['status'],'draft')
            self.assertEqual(content['body'],'正文 [1]')
            self.assertEqual(self.a.post(self.url+'/contents/'+data['id']+'/publish',json={'revision':1}).status_code,409)

    def test_model_rechecks_sources_and_cancelled_jobs_before_request(self):
        self.configure()
        for reason in ('stale_source','cancelled'):
            with self.subTest(reason=reason):
                data=self.generate(True)
                if reason=='stale_source':
                    with server.db() as c:
                        source=server.resource(c,self.pid,self.kid,'knowledge');source['version']+=1
                        server.put(c,self.pid,'knowledge',source,self.kid)
                else:
                    self.a.post(self.url+'/execution/jobs/'+data['job_id']+'/action',json={'action':'cancel'})
                with patch.object(runtime,'request_json') as remote:
                    with self.assertRaises(runtime.AdapterError): self.tick_job(data['job_id'])
                    remote.assert_not_called()

    def test_queued_model_test_requires_owner_at_execution(self):
        self.configure()
        jid=self.a.post(self.url+'/execution/jobs',json={'kind':'model_test'}).json()['id']
        with server.db() as c:
            job=server.resource(c,self.pid,jid,'execution')
            c.execute('UPDATE members SET role="editor" WHERE project_id=? AND user_id=?',(self.pid,job['actor']))
        with patch.object(runtime,'request_json') as remote:
            with self.assertRaises(runtime.AdapterError): self.tick_job(jid)
            remote.assert_not_called()

    def test_inflight_model_results_recheck_actor_and_connector(self):
        for kind in ('generate','model_test','geo_api'):
            for change in ('remove_member','downgrade','connector_version'):
                # Editor remains permitted for creation/observation; reviewer does not.
                with self.subTest(kind=kind,change=change):
                    self.setUp();self.configure()
                    generated=self.generate(True) if kind=='generate' else None
                    jid=generated['job_id'] if generated else self.a.post(self.url+'/execution/jobs',json={'kind':kind,'question':'测试供应商'}).json()['id']
                    with server.db() as c:
                        job=server.resource(c,self.pid,jid,'execution')
                        original=server.resource(c,self.pid,generated['id'],'content') if generated else None
                    def respond(*args,**kwargs):
                        with server.db() as c:
                            if change=='remove_member':
                                c.execute('DELETE FROM members WHERE project_id=? AND user_id=?',(self.pid,job['actor']))
                            elif change=='downgrade':
                                role='editor' if kind=='model_test' else 'reviewer'
                                c.execute('UPDATE members SET role=? WHERE project_id=? AND user_id=?',(role,self.pid,job['actor']))
                            else:
                                cfg=server.items(c,self.pid,'connector')[0];cfg['version']+=1
                                server.put(c,self.pid,'connector',cfg,cfg['id'])
                        return {'choices':[{'message':{'content':'不应采用的模型结果'}}],'usage':{'prompt_tokens':100,'completion_tokens':20}}
                    with patch.object(runtime,'request_json',side_effect=respond): result=self.tick_job(jid)
                    self.assertTrue(result.get('discarded'))
                    self.assertEqual(result['usage']['prompt_tokens'],100)
                    self.assertNotIn('不应采用',json.dumps(result,ensure_ascii=False))
                    with server.db() as c:
                        self.assertFalse(server.items(c,self.pid,'observation'))
                        self.assertEqual(server.items(c,self.pid,'connector')[0]['status'],'configured')
                        if generated:
                            content=server.resource(c,self.pid,generated['id'],'content')
                            self.assertEqual(content['body'],original['body'])
                            self.assertEqual(content['status'],'draft')
                            self.assertTrue(content['generation_error'])
                            self.assertNotIn('model_run',content)

    def test_local_codex_revocation_keeps_usage_and_newer_content(self):
        with patch.object(runtime.codex_local,'availability',return_value={'available':True,'reason':'fixture'}):
            self.assertEqual(self.a.post(self.url+'/execution/connectors',json={'kind':'model','transport':'codex_local','model':'gpt-6-sol'}).status_code,200)
            data=self.generate(True)
            with server.db() as c:
                job=server.resource(c,self.pid,data['job_id'],'execution')
                for row in c.execute('SELECT id,project_id FROM resources WHERE kind="execution"').fetchall():
                    if row['id']!=data['job_id']:
                        other=server.resource(c,row['project_id'],row['id'],'execution')
                        if other['status']=='queued':
                            other['status']='cancelled';server.put(c,row['project_id'],'execution',other,other['id'])
            def respond(*args):
                with server.db() as c:
                    c.execute('DELETE FROM members WHERE project_id=? AND user_id=?',(self.pid,job['actor']))
                    current=server.resource(c,self.pid,data['id'],'content')
                    current.update(body='其他成员已保存的新正文',revision=2,status='draft')
                    server.put(c,self.pid,'content',current,current['id'])
                return '已撤权任务的结果',{'transport':'codex_local','usage':{'prompt_tokens':123,'completion_tokens':4},'estimated_cost':None}
            with patch.object(runtime.codex_local,'generate',side_effect=respond),patch.object(runtime,'request_json') as api:
                server.delivery['tick']();api.assert_not_called()
        with server.db() as c:
            job=server.resource(c,self.pid,data['job_id'],'execution')
            current=server.resource(c,self.pid,data['id'],'content')
        self.assertTrue(job['result']['discarded'])
        self.assertIn('结果已舍弃',job['stage'])
        self.assertEqual(job['result']['usage']['prompt_tokens'],123)
        self.assertIsNone(job['result']['estimated_cost'])
        self.assertEqual(current['body'],'其他成员已保存的新正文')
        self.assertEqual(current['revision'],2)

    def test_model_discards_stale_inflight_answer_and_keeps_usage(self):
        self.configure();data=self.generate(True)
        original=next(x for x in self.a.get(self.url+'/state').json()['content'] if x['id']==data['id'])
        with server.db() as c:
            for row in c.execute('SELECT id,project_id FROM resources WHERE kind="execution"').fetchall():
                if row['id']!=data['job_id']:
                    job=server.resource(c,row['project_id'],row['id'],'execution');job['status']='succeeded'
                    server.put(c,row['project_id'],'execution',job,job['id'])
        def respond(*args,**kwargs):
            with server.db() as c:
                source=server.resource(c,self.pid,self.kid,'knowledge');source['status']='pending'
                server.put(c,self.pid,'knowledge',source,self.kid)
            return {'choices':[{'message':{'content':'基于失效资料的旧结果。[1]'}}],'usage':{'prompt_tokens':100,'completion_tokens':20}}
        with patch.object(runtime,'request_json',side_effect=respond) as remote:
            server.delivery['tick']()
            self.assertEqual(remote.call_count,1)
        with server.db() as c:
            job=server.resource(c,self.pid,data['job_id'],'execution')
        result=job['result']
        self.assertIn('结果已舍弃',job['stage'])
        self.assertTrue(result.get('discarded'))
        self.assertAlmostEqual(result['estimated_cost'],0.00028)
        content=next(x for x in self.a.get(self.url+'/state').json()['content'] if x['id']==data['id'])
        self.assertEqual(content['body'],original['body'])
        self.assertEqual(content['status'],'draft')
        self.assertTrue(content['knowledge_outdated'])
        self.assertTrue(content['generation_error'])
        self.assertNotIn('model_run',content)
        self.assertEqual(self.a.post(self.url+'/contents/'+data['id']+'/review',json={'revision':1,'action':'submit'}).status_code,409)

    def test_report_separates_discarded_model_results_and_keeps_cost(self):
        with server.db() as c:
            server.put(c,self.pid,'execution',{'job_type':'generate','status':'succeeded','stage':'已完成',
                'result':{'discarded':True,'reason':'来源改变<script>unsafe</script>','usage':{'prompt_tokens':100,'completion_tokens':20},'estimated_cost':0.00028,'currency':'USD'},'error':''})
            server.put(c,self.pid,'execution',{'job_type':'generate','status':'succeeded','stage':'已完成',
                'result':{'content_id':'fixture-retained'},'error':''})
            server.put(c,self.pid,'execution',{'job_type':'model_test','status':'succeeded','stage':'已完成','result':{},'error':''})
        report=self.a.get(self.url+'/report')
        self.assertEqual(report.status_code,200,report.text)
        self.assertIn('已保存生成结果 1 次；结果已舍弃 1 次',report.text)
        self.assertIn('本次未产出可用稿件',report.text)
        self.assertIn('100 输入 / 20 输出',report.text)
        self.assertIn('USD 0.000280',report.text)
        self.assertIn('来源改变&lt;script&gt;unsafe&lt;/script&gt;',report.text)
        self.assertNotIn('<script>unsafe</script>',report.text)
        self.assertEqual(self.b.get(self.url+'/report').status_code,404)
        checks=self.a.get(self.url+'/readiness').json()['checks']
        self.assertFalse(next(x for x in checks if x['name']=='已产出真实模型草稿')['ok'])
        with server.db() as c:
            server.put(c,self.pid,'execution',{'job_type':'generate','status':'succeeded','stage':'已完成',
                'result':{'discarded':True,'reason':'旧任务未记录用量'},'error':''})
        report=self.a.get(self.url+'/report').text
        self.assertIn('已保存生成结果 1 次；结果已舍弃 2 次',report)
        self.assertIn('— 输入 / — 输出',report)
        self.assertIn('费用未取得或未配置单价',report)

    def rebuild_fixture(self):
        with server.db() as c:
            kid=server.put(c,self.pid,'knowledge',{'title':'历史提炼','category':'技术资料','body':'旧工况结论需要重新提炼。','source':'原稿','version':2,'status':'pending','derived':True,'knowledge_outdated':True,'source_ids':[self.kid],'source_snapshots':[{'id':self.kid,'version':1}]})
        return kid,{'version':2,'title':'新版提炼','body':'根据原资料重新明确图纸、材料与公差的验收条件。','note':'重新核实使用边界和验收条件','sources':[{'id':self.kid,'version':1}]}

    def test_rebuild_derived_preserves_old_draft_and_requires_new_confirmation(self):
        kid,data=self.rebuild_fixture();endpoint=self.url+'/knowledge/'+kid+'/rebuild'
        with server.db() as c: before=server.resource(c,self.pid,kid,'knowledge')
        response=self.a.post(endpoint,json=data)
        self.assertEqual(response.status_code,200,response.text)
        new_id=response.json()['id']
        self.assertNotEqual(kid,new_id)
        repeated=self.a.post(endpoint,json=data)
        self.assertEqual(repeated.json(),{'id':new_id,'created':False})
        with server.db() as c:
            self.assertEqual(server.resource(c,self.pid,kid,'knowledge'),before)
            doc=server.resource(c,self.pid,new_id,'knowledge')
        self.assertEqual(doc['status'],'pending');self.assertEqual(doc['version'],1)
        self.assertEqual(doc['rebuild_from']['id'],kid)
        self.assertEqual(doc['rebuild_note'],data['note'])
        self.assertEqual(len(doc['source_snapshots'][0]['body_sha256']),64)
        self.assertNotIn('confirmation_history',doc)
        self.assertEqual(self.a.post(self.url+'/generate',json={'title':'重建稿应用','skill_id':'faq','knowledge_ids':[new_id],'channels':['知乎']}).status_code,409)
        self.assertEqual(self.a.post(self.url+'/knowledge/'+new_id+'/confirm',json={'version':1}).status_code,200)
        self.assertEqual(self.a.post(self.url+'/generate',json={'title':'重建稿应用','skill_id':'faq','knowledge_ids':[new_id],'channels':['知乎']}).status_code,200)
        self.a.put(self.url+'/knowledge/'+self.kid+'/revise',json={'version':1,'body':'再次变更的原资料，必须重新验证条件。'})
        updated=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==new_id)
        self.assertTrue(updated['knowledge_outdated'])

    def test_rebuild_retry_rejects_changed_or_confirmed_replacement_without_writes(self):
        for change in ('revision','confirmed','legacy_body','legacy_sources'):
            with self.subTest(change=change):
                kid,data=self.rebuild_fixture();endpoint=self.url+'/knowledge/'+kid+'/rebuild'
                created=self.a.post(endpoint,json=data)
                self.assertEqual(created.status_code,200,created.text)
                new_id=created.json()['id']
                if change=='revision':
                    self.assertEqual(self.a.put(self.url+'/knowledge/'+new_id+'/revise',json={'version':1,'body':'技术人员另行修订的新结论，请保留这一版本。'}).status_code,200)
                elif change=='confirmed':
                    self.assertEqual(self.a.post(self.url+'/knowledge/'+new_id+'/confirm',json={'version':1}).status_code,200)
                else:
                    with server.db() as c:
                        doc=server.resource(c,self.pid,new_id,'knowledge')
                        if change=='legacy_body': doc['body']='版本未变但正文已经不同的历史记录。'
                        else: doc['source_snapshots'][0]['body_sha256']='different'
                        server.put(c,self.pid,'knowledge',doc,new_id)
                with server.db() as c:
                    before=server.items(c,self.pid,'knowledge')
                    event_count=c.execute('select count(*) from events where project_id=?',(self.pid,)).fetchone()[0]
                retry=self.a.post(endpoint,json=data)
                self.assertEqual(retry.status_code,409,retry.text)
                self.assertIn('重建稿已变化',retry.json()['detail'])
                with server.db() as c:
                    self.assertEqual(server.items(c,self.pid,'knowledge'),before)
                    self.assertEqual(c.execute('select count(*) from events where project_id=?',(self.pid,)).fetchone()[0],event_count)

    def test_rebuild_rejects_stale_sources_and_unauthorized_or_unchanged_drafts(self):
        kid,data=self.rebuild_fixture();endpoint=self.url+'/knowledge/'+kid+'/rebuild'
        self.assertEqual(self.b.post(endpoint,json=data).status_code,404)
        for change,code in (({'version':1},409),({'body':' 旧工况结论需要重新提炼。\n'},422),({'sources':[]},422),({'sources':data['sources']*2},422),({'sources':[{'id':kid,'version':2}]},422),({'sources':[{'id':self.kid,'version':99}]},409)):
            self.assertEqual(self.a.post(endpoint,json={**data,**change}).status_code,code)
        other=next(p['id'] for p in self.b.get('/api/me').json()['projects'] if '澄川' in p['name'])
        foreign=self.b.get('/api/projects/'+other+'/state').json()['knowledge'][0]['id']
        self.assertEqual(self.a.post(endpoint,json={**data,'sources':[{'id':foreign,'version':1}]}).status_code,404)
        identity=self.b.get('/api/me').json()['identity']
        self.a.post(self.url+'/members',json={'identity':identity,'role':'reviewer'})
        self.assertEqual(self.b.post(endpoint,json=data).status_code,403)
        with server.db() as c:
            source=server.resource(c,self.pid,self.kid,'knowledge');source['status']='pending'
            server.put(c,self.pid,'knowledge',source,self.kid)
        self.assertEqual(self.a.post(endpoint,json=data).status_code,409)
        with server.db() as c:
            self.assertFalse(any(x.get('rebuild_from') for x in server.items(c,self.pid,'knowledge')))

    def test_model_uses_snapshot_and_records_cost(self):
        self.configure(); self.a.post(self.url + '/brand', json={'voice': '专业克制'})
        data = self.generate(True)
        response = {'choices': [{'message': {'content': '先确认材料要求与图纸版本。[1]'}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 20}}
        with patch.object(runtime, 'request_json', return_value=response) as call:
            result = self.tick_job(data['job_id'])
        messages = call.call_args.kwargs['data']['messages']
        self.assertIn('专业克制', messages[0]['content'])
        self.assertIn('图纸', messages[1]['content'])
        self.assertAlmostEqual(result['estimated_cost'], 0.00028)
        content = next(x for x in self.a.get(self.url + '/state').json()['content'] if x['id'] == data['id'])
        self.assertEqual(content['status'], 'draft')
        self.assertIn('[1]', content['body'])
        self.assertEqual(content['quality']['status'], 'checks_passed')
        self.assertEqual(self.a.post(self.url + '/contents/' + data['id'] + '/review', json={'revision': 1, 'action': 'submit'}).status_code, 200)

    def test_cancel_and_report_redaction_and_escaping(self):
        self.configure(); generated = self.generate(True)
        r = self.a.post(self.url + '/execution/jobs/' + generated['job_id'] + '/action', json={'action': 'cancel'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.a.post(self.url + '/contents/' + generated['id'] + '/review', json={'revision': 1, 'action': 'submit'}).status_code, 409)
        self.a.post(self.url + '/leads', json={'company': 'test', 'contact': 'PRIVATE-PHONE-123', 'need': '产品咨询'})
        with server.db() as c:
            ct = server.resource(c, self.pid, generated['id'], 'content')
            ct.update(title='<script>alert(1)</script>')
            server.put(c, self.pid, 'content', ct, ct['id'])
        report = self.a.get(self.url + '/report')
        self.assertEqual(report.status_code, 200, report.text)
        self.assertNotIn('PRIVATE-PHONE-123', report.text)
        self.assertNotIn('private-test-secret', report.text)
        self.assertNotIn('<script>', report.text)
        self.assertIn('演示空间', report.text)
        self.assertEqual(self.b.get(self.url + '/report').status_code, 404)
        self.assertEqual(self.b.get(self.url + '/readiness').status_code, 404)

    def test_knowledge_audit_preview_and_report_distinguish_current_and_history(self):
        kid=self.a.post(self.url+'/knowledge',json={'title':'技术依据<script>audit</script>','body':'第一版审核正文，不含其他企业资料。','category':'产品','source':'原始资料'}).json()['id']
        self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':1})
        state=self.a.get(self.url+'/state').json()
        doc=next(k for k in state['knowledge'] if k['id']==kid)
        self.assertEqual(doc['review_summary']['history'][0]['label'],'当前版本确认')
        self.assertTrue(doc['review_summary']['effective_confirmed'])
        self.a.put(self.url+'/knowledge/'+kid+'/revise',json={'version':1,'body':'第二版已变更，必须重新核准正文。'})
        doc=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==kid)
        self.assertFalse(doc['review_summary']['effective_confirmed'])
        self.assertEqual(doc['review_summary']['history'][0]['label'],'历史版本确认')
        report=self.a.get(self.url+'/report')
        self.assertIn('知识确认记录',report.text)
        self.assertIn('历史版本确认',report.text)
        self.assertIn(doc['confirmation_history'][0]['body_sha256'],report.text)
        self.assertIn('&lt;script&gt;audit&lt;/script&gt;',report.text)
        self.assertNotIn('<script>audit</script>',report.text)
        self.assertEqual(self.b.get(self.url+'/report').status_code,404)
        self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':2})
        with server.db() as c:
            record=server.resource(c,self.pid,kid,'knowledge')
            record['knowledge_outdated']=True
            server.put(c,self.pid,'knowledge',record,kid)
        doc=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==kid)
        self.assertEqual(doc['review_summary']['history'][-1]['label'],'当前版本确认已失效')
        self.assertFalse(doc['review_summary']['effective_confirmed'])
        self.assertIn('当前版本确认已失效',self.a.get(self.url+'/report').text)
        with server.db() as c:
            self.assertNotIn('review_summary',server.resource(c,self.pid,kid,'knowledge'))

    def test_report_readiness_excludes_stale_confirmed_knowledge(self):
        with server.db() as c:
            for doc in server.items(c,self.pid,'knowledge'):
                doc.update(status='confirmed',derived=True,source_ids=['missing'],source_snapshots=[{'id':'missing','version':1}])
                server.put(c,self.pid,'knowledge',doc,doc['id'])
        checks=self.a.get(self.url+'/readiness').json()['checks']
        self.assertFalse(next(x for x in checks if x['name']=='企业事实已核准')['ok'])
        report=self.a.get(self.url+'/report').text
        self.assertIn('当前有效确认资料 0 份',report)
        self.assertIn('未留存确认记录',report)
        with server.db() as c:
            self.assertTrue(all(k['status']=='confirmed' for k in server.items(c,self.pid,'knowledge')))

    def test_effective_content_approval_excludes_stale_sources_without_rewriting_history(self):
        rid=self.generate()['id']
        for action in ('submit','approve'):
            self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':action}).status_code,200)
        self.assertEqual(self.a.get(self.url+'/metrics').json()['approved'],1)
        with server.db() as c:
            k=server.resource(c,self.pid,self.kid,'knowledge')
            k['version']+=1
            server.put(c,self.pid,'knowledge',k,self.kid)
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).status_code,409)
        self.assertEqual(self.a.get(self.url+'/metrics').json()['approved'],0)
        state=self.a.get(self.url+'/state').json()
        doc=next(x for x in state['content'] if x['id']==rid)
        self.assertTrue(doc['approval_summary']['sources_outdated'])
        self.assertFalse(doc['approval_summary']['effective_approved'])
        self.assertEqual(state['stats']['approved'],0)
        checks=self.a.get(self.url+'/readiness').json()['checks']
        self.assertFalse(next(x for x in checks if x['name']=='当前版本完成客户审核')['ok'])
        report=self.a.get(self.url+'/report').text
        # Both the seeded pending article and the newly approved article cite this source.
        self.assertIn('知识已过期内容 2 篇',report)
        self.assertIn('引用知识版本不一致',report)
        with server.db() as c:
            raw=server.resource(c,self.pid,rid,'content')
            self.assertEqual(raw['status'],'approved')
            self.assertEqual(raw['approved_revision'],1)
            self.assertNotIn('approval_summary',raw)
        self.assertEqual(self.b.get(self.url+'/metrics').status_code,404)

    def test_content_approval_summary_checks_revision_and_missing_or_foreign_sources(self):
        rid=self.generate()['id']
        with server.db() as c:
            original=server.resource(c,self.pid,rid,'content')
        other=next(p['id'] for p in self.b.get('/api/me').json()['projects'] if '澄川' in p['name'])
        foreign=self.b.get('/api/projects/'+other+'/state').json()['knowledge'][0]['id']
        for changes in ({'approved_revision':0},{'sources':[{'id':'missing','version':1}]},{'sources':[{'id':foreign,'version':1}]},{'channels':[]}):
            with self.subTest(changes=changes):
                with server.db() as c:
                    server.put(c,self.pid,'content',{**original,'status':'approved','approved_revision':1,**changes},rid)
                self.assertEqual(self.a.get(self.url+'/metrics').json()['approved'],0)
                self.assertEqual(self.a.get(self.url+'/report').status_code,200)

    def test_unknown_publication_reconcile_without_reposting(self):
        self.configure('wordpress'); rid = self.generate()['id']
        for action in ['submit', 'approve']: self.a.post(self.url + '/contents/' + rid + '/review', json={'revision': 1, 'action': action})
        self.a.post(self.url + '/contents/' + rid + '/publish', json={'revision': 1})
        pub = next(x for x in self.a.get(self.url + '/state').json()['publication'] if x['content_id'] == rid and x['channel'] == '企业官网')
        jid = self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).json()['id']
        with server.db() as c:
            job = server.resource(c,self.pid,jid,'execution');job.update(status='unknown',stage='网络超时');server.put(c,self.pid,'execution',job,jid)
        self.assertEqual(self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).status_code,409)
        reconcile = self.a.post(self.url + '/execution/jobs/' + jid + '/action',json={'action':'reconcile'})
        self.assertEqual(reconcile.status_code,200,reconcile.text)
        html = ''.join('<p>' + runtime.html.escape(x).replace('\n','<br>') + '</p>' for x in pub['body_snapshot'].split('\n\n'))
        remote = [{'id':99,'status':'draft','title':{'raw':pub['title']},'content':{'raw':html},'link':'https://example.com/?p=99'}]
        with patch.object(runtime,'request_json',return_value=remote) as call:
            self.tick_job(reconcile.json()['id'])
        self.assertEqual(call.call_args.args[1],'GET')
        s=self.a.get(self.url+'/state').json()
        self.assertEqual(next(x for x in s['execution'] if x['id']==jid)['status'],'reconciled')
        self.assertEqual(next(x for x in s['publication'] if x['id']==pub['id'])['status'],'wp_draft')

    def test_variant_package_and_knowledge_change_gate(self):
        rid = self.generate()['id']
        r = self.a.put(self.url + '/contents/' + rid + '/variant', json={'revision': 1, 'channel': '知乎', 'title': '知乎采购回答', 'body': '确认图纸与材料。[1]', 'cta_url': 'https://example.com/contact'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.a.get(self.url + '/contents/' + rid + '/package').status_code, 409)
        for action in ['submit', 'approve']:
            self.assertEqual(self.a.post(self.url + '/contents/' + rid + '/review', json={'revision': 2, 'action': action}).status_code, 200)
        pack = self.a.get(self.url + '/contents/' + rid + '/package').json()
        self.assertEqual(pack['platform_payloads']['知乎']['title'], '知乎采购回答')
        self.assertFalse(pack['published']); self.assertEqual(len(pack['sha256']), 64)
        ids = self.a.post(self.url + '/contents/' + rid + '/publish', json={'revision': 2}).json()['ids']
        revised = self.a.put(self.url + '/knowledge/' + self.kid + '/revise', json={'version': 1, 'body': '最新技术要求：请提供完整图纸。'})
        self.assertEqual(revised.status_code, 200, revised.text)
        self.assertEqual(self.a.get(self.url + '/contents/' + rid + '/package').status_code, 409)
        s = self.a.get(self.url + '/state').json()
        self.assertTrue(all(x['status'] == 'cancelled' for x in s['publication'] if x['id'] in ids))
        self.assertEqual(self.a.post(self.url + '/contents/' + rid + '/review', json={'revision': 3, 'action': 'submit'}).status_code, 409)

    def test_faq_dependencies_invalidate_transitive_content_and_search(self):
        def faq(source, question):
            r=self.a.post(self.url+'/faq',json={'question':question,'answer':'独有旧值ABC991需要依据参数核准。','source_ids':[source]})
            self.assertEqual(r.status_code,200,r.text)
            f=next(x for x in self.a.get(self.url+'/state').json()['faq'] if x['id']==r.json()['id'])
            self.assertEqual(self.a.post(self.url+'/knowledge/'+f['knowledge_id']+'/confirm',json={'version':1}).status_code,200)
            return f['knowledge_id']
        first=faq(self.kid,'一级工况问答');second=faq(first,'二级工况问答')
        r=self.a.post(self.url+'/generate',json={'title':'工况回答','skill_id':'faq','knowledge_ids':[second],'channels':['知乎']})
        rid=r.json()['id']
        for action in ('submit','approve'):
            self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':action}).status_code,200)
        self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1})
        result=self.a.put(self.url+'/knowledge/'+self.kid+'/revise',json={'version':1,'body':'原始资料更新，需要使用新参数进行评估。'})
        self.assertEqual(result.status_code,200,result.text)
        state=self.a.get(self.url+'/state').json()
        for kid in (first,second):
            k=next(x for x in state['knowledge'] if x['id']==kid)
            self.assertEqual(k['status'],'pending')
            self.assertTrue(k['knowledge_outdated'])
            self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':k['version']}).status_code,409)
        self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'ABC991'}).json()['matches'])
        content=next(x for x in state['content'] if x['id']==rid)
        self.assertEqual(content['status'],'draft');self.assertIsNone(content['approved_revision'])
        self.assertTrue(all(p['status']=='cancelled' for p in state['publication'] if p['content_id']==rid))
        self.assertEqual(self.a.post(self.url+'/generate',json={'title':'不可复用旧问答','skill_id':'faq','knowledge_ids':[second],'channels':['知乎']}).status_code,409)

    def test_faq_cannot_bind_pending_or_cross_tenant_sources(self):
        pending=self.a.post(self.url+'/knowledge',json={'title':'未确认资料','body':'这份资料仍然等待技术审核','category':'产品','source':'客户资料'}).json()['id']
        data={'question':'能否直接使用？','answer':'需要等待原始资料核准。','source_ids':[pending]}
        self.assertEqual(self.a.post(self.url+'/faq',json=data).status_code,409)
        other=next(p['id'] for p in self.b.get('/api/me').json()['projects'] if '澄川' in p['name'])
        foreign=self.b.get('/api/projects/'+other+'/state').json()['knowledge'][0]['id']
        self.assertEqual(self.a.post(self.url+'/faq',json={**data,'source_ids':[foreign]}).status_code,404)

    def test_knowledge_confirmation_binds_preview_version_and_keeps_audit(self):
        kid=self.a.post(self.url+'/knowledge',json={'title':'待审核参数','body':'第一版工况参数，需要企业技术人员核实。','category':'产品','source':'客户原稿'}).json()['id']
        endpoint=self.url+'/knowledge/'+kid+'/confirm'
        self.assertEqual(self.a.put(self.url+'/knowledge/'+kid+'/revise',json={'version':1,'body':'第二版参数，已修改适用工况，审核人尚未阅读。'}).status_code,200)
        self.assertEqual(self.a.post(endpoint,json={'version':1}).status_code,409)
        doc=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==kid)
        self.assertEqual(doc['status'],'pending')
        self.assertEqual(self.a.post(endpoint,json={}).status_code,422)
        self.assertEqual(self.a.post(endpoint,json={'version':2}).status_code,200)
        self.assertEqual(self.a.post(endpoint,json={'version':2}).status_code,200)
        doc=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==kid)
        self.assertEqual(len(doc['confirmation_history']),1)
        audit=doc['confirmation_history'][0]
        self.assertEqual(audit['version'],2)
        self.assertEqual(audit['actor'],self.a.get('/api/me').json()['identity'])
        self.assertEqual(audit['body_sha256'],runtime.hashlib.sha256(doc['body'].encode()).hexdigest())
        self.assertEqual(self.b.post(endpoint,json={'version':2}).status_code,404)
        identity=self.b.get('/api/me').json()['identity']
        self.a.post(self.url+'/members',json={'identity':identity,'role':'editor'})
        self.assertEqual(self.b.post(endpoint,json={'version':2}).status_code,403)

    def test_derived_knowledge_invalidates_transitive_faq_and_content(self):
        with server.db() as c:
            derived=server.put(c,self.pid,'knowledge',{'title':'技术提炼','body':'派生参数DERIVED881依据原文核准。','category':'产品','source':'原资料','status':'confirmed','version':1,'derived':True,'source_ids':[self.kid],'source_snapshots':[{'id':self.kid,'version':1}]})
        f=self.a.post(self.url+'/faq',json={'question':'派生资料如何应用？','answer':'引用已核准技术提炼。','source_ids':[derived]})
        self.assertEqual(f.status_code,200,f.text)
        faq=next(x for x in self.a.get(self.url+'/state').json()['faq'] if x['id']==f.json()['id'])
        self.a.post(self.url+'/knowledge/'+faq['knowledge_id']+'/confirm',json={'version':1})
        r=self.a.post(self.url+'/generate',json={'title':'派生资料文章','skill_id':'faq','knowledge_ids':[faq['knowledge_id']],'channels':['知乎']})
        rid=r.json()['id']
        for action in ('submit','approve'):
            self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':action}).status_code,200)
        self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1})
        r=self.a.put(self.url+'/knowledge/'+self.kid+'/revise',json={'version':1,'body':'原文技术条件已发生调整，请重新提炼。'})
        self.assertEqual(r.status_code,200,r.text)
        state=self.a.get(self.url+'/state').json()
        for kid in (derived,faq['knowledge_id']):
            k=next(x for x in state['knowledge'] if x['id']==kid)
            self.assertEqual(k['version'],2)
            self.assertEqual(k['status'],'pending')
            self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':2}).status_code,409)
        self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'DERIVED881'}).json()['matches'])
        self.assertTrue(all(x['status']=='cancelled' for x in state['publication'] if x['content_id']==rid))
        self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/package').status_code,409)

    def test_derived_knowledge_rejects_missing_stale_and_foreign_evidence(self):
        other=next(p['id'] for p in self.b.get('/api/me').json()['projects'] if '澄川' in p['name'])
        foreign=self.b.get('/api/projects/'+other+'/state').json()['knowledge'][0]['id']
        for snapshots in (None,[],[{'id':self.kid,'version':99}],[{'id':foreign,'version':1}]):
            with self.subTest(snapshots=snapshots):
                with server.db() as c:
                    doc={'title':'历史提炼','body':'旧提炼LEGACY882待核对。','category':'产品','source':'历史整理','status':'confirmed','version':1,'derived':True,'source_ids':[self.kid]}
                    if snapshots is not None: doc['source_snapshots']=snapshots
                    kid=server.put(c,self.pid,'knowledge',doc)
                self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':1}).status_code,409)
                self.assertEqual(self.a.post(self.url+'/generate',json={'title':'旧稿不可生成','skill_id':'faq','knowledge_ids':[kid],'channels':['知乎']}).status_code,409)
        self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'LEGACY882'}).json()['matches'])
        with server.db() as c:
            doc.update(source_ids=[foreign],source_snapshots=[{'id':foreign,'version':1}])
            kid=server.put(c,self.pid,'knowledge',doc)
        self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':1}).status_code,409)
        with server.db() as c:
            doc.update(source_ids=[self.kid],source_snapshots=[{'id':self.kid,'version':1}])
            kid=server.put(c,self.pid,'knowledge',doc)
            source=server.resource(c,self.pid,self.kid,'knowledge')
            source['status']='pending'
            server.put(c,self.pid,'knowledge',source,self.kid)
        self.assertEqual(self.a.post(self.url+'/knowledge/'+kid+'/confirm',json={'version':1}).status_code,409)

    def test_legacy_faq_snapshot_cannot_be_reconfirmed_or_searched(self):
        r=self.a.post(self.url+'/faq',json={'question':'旧工况问答','answer':'历史参数LEGACY991','source_ids':[self.kid]})
        f=next(x for x in self.a.get(self.url+'/state').json()['faq'] if x['id']==r.json()['id'])
        self.a.post(self.url+'/knowledge/'+f['knowledge_id']+'/confirm',json={'version':1})
        rid=self.a.post(self.url+'/generate',json={'title':'历史审批问答稿','skill_id':'faq','knowledge_ids':[f['knowledge_id']],'channels':['知乎']}).json()['id']
        for action in ('submit','approve'):
            self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':action}).status_code,200)
        with server.db() as c:
            source=server.resource(c,self.pid,self.kid,'knowledge')
            source['version']+=1
            server.put(c,self.pid,'knowledge',source,self.kid)
        self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'LEGACY991'}).json()['matches'])
        self.assertEqual(self.a.post(self.url+'/knowledge/'+f['knowledge_id']+'/confirm',json={'version':1}).status_code,409)
        doc=next(k for k in self.a.get(self.url+'/state').json()['knowledge'] if k['id']==f['knowledge_id'])
        self.assertTrue(doc['knowledge_outdated'])
        self.assertEqual(doc['status'],'pending')
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':1}).status_code,409)
        self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/package').status_code,409)

    def test_reconcile_revoked_version_preserves_remote_evidence_without_reapproval(self):
        for remote_status in ('draft', 'publish'):
            with self.subTest(remote_status=remote_status):
                pub, jid = self.publication_fixture()
                with server.db() as c:
                    job = server.resource(c, self.pid, jid, 'execution')
                    job['status'] = 'unknown'
                    server.put(c, self.pid, 'execution', job, jid)
                changed = self.a.put(self.url + '/contents/' + pub['content_id'], json={
                    'revision': 1, 'title': '新修订稿', 'body': '重新核准后的新内容', 'channels': ['企业官网']})
                self.assertEqual(changed.status_code, 200, changed.text)
                rec = self.a.post(self.url + '/execution/jobs/' + jid + '/action', json={'action':'reconcile'})
                self.assertEqual(rec.status_code, 200, rec.text)
                rendered = ''.join('<p>' + runtime.html.escape(x).replace('\n', '<br>') + '</p>' for x in pub['body_snapshot'].split('\n\n'))
                remote = [{'id':101,'status':remote_status,'title':{'raw':pub['title']},
                           'content':{'raw':rendered},'link':'https://example.com/old-version'}]
                with patch.object(runtime, 'request_json', return_value=remote) as call:
                    result = self.tick_job(rec.json()['id'])
                self.assertTrue(result['requires_attention'])
                self.assertEqual(call.call_count, 1)
                self.assertEqual(call.call_args.args[1], 'GET')
                state = self.a.get(self.url + '/state').json()
                current = next(x for x in state['content'] if x['id'] == pub['content_id'])
                saved = next(x for x in state['publication'] if x['id'] == pub['id'])
                self.assertEqual((current['revision'],current['status'],current['approved_revision']), (2,'draft',None))
                self.assertEqual(saved['status'], 'cancelled')
                self.assertEqual(saved['remote_evidence']['platform_status'],remote_status)
                self.assertEqual(saved['remote_evidence']['revision'],1)
                self.assertEqual(self.a.get(self.url + '/metrics').json()['published'],0)
                self.assertEqual(next(x for x in state['execution'] if x['id']==jid)['status'],'reconciled')
                checks = self.a.get(self.url + '/readiness').json()['checks']
                self.assertFalse(next(x for x in checks if x['name']=='执行异常已处理')['ok'])
                report = self.a.get(self.url + '/report')
                self.assertIn('旧版远端记录待处理',report.text)
                self.assertIn('https://example.com/old-version',report.text)
                self.assertEqual(self.b.get(self.url + '/report').status_code,404)
                self.assertEqual(self.a.post(self.url + '/execution/jobs',json={'kind':'wp_draft','resource_id':pub['id']}).status_code,409)

    def test_external_draft_and_publish_restore_approved_payload(self):
        self.configure('wordpress'); rid = self.generate()['id']
        for action in ['submit', 'approve']: self.a.post(self.url + '/contents/' + rid + '/review', json={'revision': 1, 'action': action})
        self.a.post(self.url + '/contents/' + rid + '/publish', json={'revision': 1})
        pub = next(x for x in self.a.get(self.url + '/state').json()['publication'] if x['content_id'] == rid and x['channel'] == '企业官网')
        job = self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).json()
        duplicate = self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).json()
        self.assertEqual(job['id'], duplicate['id'])
        with patch.object(runtime, 'request_json', return_value={'id': 91, 'status': 'draft', 'link': 'https://example.com/?p=91'}):
            self.tick_job(job['id'])
        publish_job = self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_publish', 'resource_id': pub['id']}).json()
        with patch.object(runtime, 'request_json', return_value={'id': 91, 'status': 'publish', 'link': 'https://example.com/article'}) as call:
            self.tick_job(publish_job['id'])
        self.assertEqual(call.call_args.kwargs['data']['title'], pub['title'])
        self.assertIn('content', call.call_args.kwargs['data'])
        self.assertEqual(self.a.get(self.url + '/metrics').json()['published'], 1)

    def publication_fixture(self):
        self.configure('wordpress')
        rid = self.generate()['id']
        for action in ('submit', 'approve'):
            self.assertEqual(self.a.post(self.url + '/contents/' + rid + '/review', json={'revision': 1, 'action': action}).status_code, 200)
        self.a.post(self.url + '/contents/' + rid + '/publish', json={'revision': 1})
        pub = next(x for x in self.a.get(self.url + '/state').json()['publication'] if x['content_id'] == rid and x['channel'] == '企业官网')
        jid = self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).json()['id']
        return pub, jid

    def disposition_fixture(self):
        pub, jid = self.publication_fixture()
        evidence = {'platform_status':'publish','external_id':101,'url':'https://example.com/old',
                    'observed_at':server.now(),'revision':1,'original_job_id':jid}
        with server.db() as c:
            saved = server.resource(c,self.pid,pub['id'],'publication')
            saved.update(status='cancelled',requires_attention=True,remote_evidence=evidence)
            server.put(c,self.pid,'publication',saved,pub['id'])
            job = server.resource(c,self.pid,jid,'execution');job['status']='reconciled'
            server.put(c,self.pid,'execution',job,jid)
        data={'version':0,'expected_evidence':evidence,'outcome':'removed',
              'note':'客户确认原文需要撤下，运营人员已在平台处理并提供处理记录。',
              'evidence_url':'https://example.com/client-confirmation'}
        return pub, data

    def test_disposition_history_reopen_and_no_remote_mutation(self):
        pub, data = self.disposition_fixture()
        url=self.url+'/publications/'+pub['id']+'/disposition'
        with patch.object(runtime,'request_json') as call:
            result=self.a.post(url,json=data)
            self.assertEqual(result.status_code,200,result.text)
            self.assertFalse(result.json()['external_changed'])
            call.assert_not_called()
        state=self.a.get(self.url+'/state').json()
        saved=next(p for p in state['publication'] if p['id']==pub['id'])
        self.assertFalse(saved['requires_attention'])
        self.assertEqual(saved['status'],'cancelled')
        self.assertEqual(saved['remote_evidence'],data['expected_evidence'])
        self.assertEqual(saved['disposition_history'][0]['verification'],'manual_unverified')
        self.assertEqual(self.a.get(self.url+'/metrics').json()['published'],0)
        self.assertEqual(self.a.post(url,json=data).status_code,409)
        data.update(version=1,outcome='reopen',evidence_url='',note='后续复核发现处理依据不足，需要重新打开该旧版记录并补充证据。')
        self.assertEqual(self.a.post(url,json=data).status_code,200)
        saved=next(p for p in self.a.get(self.url+'/state').json()['publication'] if p['id']==pub['id'])
        self.assertTrue(saved['requires_attention'])
        self.assertEqual(len(saved['disposition_history']),2)
        self.assertEqual(saved['disposition_history'][0]['outcome'],'removed')
        self.assertIn('人工登记，未验证远端变更',self.a.get(self.url+'/report').text)

    def test_disposition_access_evidence_and_conflict_gates(self):
        pub,data=self.disposition_fixture();url=self.url+'/publications/'+pub['id']+'/disposition'
        self.assertEqual(self.b.post(url,json=data).status_code,404)
        identity=self.b.get('/api/me').json()['identity']
        self.a.post(self.url+'/members',json={'identity':identity,'role':'editor'})
        self.assertEqual(self.b.post(url,json=data).status_code,403)
        self.assertEqual(self.a.post(url,json={**data,'evidence_url':''}).status_code,422)
        self.assertEqual(self.a.post(url,json={**data,'note':' '*30}).status_code,422)
        self.assertEqual(self.a.post(url,json={**data,'evidence_url':'javascript:alert(1)'}).status_code,422)
        self.assertEqual(self.a.post(url,json={**data,'expected_evidence':{**data['expected_evidence'],'external_id':999}}).status_code,409)
        self.a.post(self.url+'/members',json={'identity':identity,'role':'reviewer'})
        self.assertEqual(self.b.post(url,json=data).status_code,200)

    def test_manual_receipt_cancels_queued_wordpress_without_sending(self):
        pub, jid = self.publication_fixture()
        receipt = self.a.post(self.url + '/publications/' + pub['id'] + '/receipt', json={'url': 'https://example.com/manually-published'})
        self.assertEqual(receipt.status_code, 200, receipt.text)
        state = self.a.get(self.url + '/state').json()
        self.assertEqual(next(j for j in state['execution'] if j['id'] == jid)['status'], 'cancelled')
        saved = next(p for p in state['publication'] if p['id'] == pub['id'])
        self.assertEqual(saved['method'], 'manual')
        self.assertEqual(saved['status'], 'recorded')
        with patch.object(runtime, 'request_json') as remote:
            with self.assertRaises(runtime.AdapterError): self.tick_job(jid)
            remote.assert_not_called()
        self.assertEqual(self.a.post(self.url + '/execution/jobs', json={'kind': 'wp_draft', 'resource_id': pub['id']}).status_code, 409)

    def test_manual_receipt_rejects_stale_knowledge_without_cancelling_jobs(self):
        pub, jid = self.publication_fixture()
        with server.db() as c:
            source=server.resource(c,self.pid,self.kid,'knowledge')
            source['version']+=1
            server.put(c,self.pid,'knowledge',source,self.kid)
            before_events=c.execute('select count(*) from events where project_id=?',(self.pid,)).fetchone()[0]
        endpoint=self.url+'/publications/'+pub['id']+'/receipt'
        result=self.a.post(endpoint,json={'url':'https://example.com/manual'})
        self.assertEqual(result.status_code,409,result.text)
        with server.db() as c:
            saved=server.resource(c,self.pid,pub['id'],'publication')
            self.assertEqual(saved['status'],'awaiting_connector')
            self.assertEqual(saved['url'],'')
            self.assertEqual(server.resource(c,self.pid,jid,'execution')['status'],'queued')
            self.assertEqual(c.execute('select count(*) from events where project_id=?',(self.pid,)).fetchone()[0],before_events)
        self.assertEqual(self.a.get(self.url+'/metrics').json()['published'],0)
        with patch.object(runtime,'request_json') as remote:
            with self.assertRaises(runtime.AdapterError): self.tick_job(jid)
            remote.assert_not_called()
        self.assertEqual(self.b.post(endpoint,json={'url':'https://example.com/manual'}).status_code,404)

    def test_manual_receipt_rejects_lost_approval_or_changed_publication_channel(self):
        pub,jid=self.publication_fixture()
        with server.db() as c:
            original=server.resource(c,self.pid,pub['content_id'],'content')
        for changes in ({'status':'draft'},{'approved_revision':None},{'revision':2,'approved_revision':2},{'channels':['知乎']}):
            with self.subTest(changes=changes):
                with server.db() as c:
                    server.put(c,self.pid,'content',{**original,**changes},original['id'])
                response=self.a.post(self.url+'/publications/'+pub['id']+'/receipt',json={'url':'https://example.com/manual'})
                self.assertEqual(response.status_code,409,response.text)
                with server.db() as c:
                    self.assertEqual(server.resource(c,self.pid,jid,'execution')['status'],'queued')
                    self.assertEqual(server.resource(c,self.pid,pub['id'],'publication')['status'],'awaiting_connector')

    def test_wordpress_rejects_removed_channel_at_queue_and_execution(self):
        for kind in ('wp_draft','wp_publish'):
            with self.subTest(kind=kind):
                pub,jid=self.publication_fixture()
                if kind=='wp_publish':
                    with patch.object(runtime,'request_json',return_value={'id':101,'status':'draft','link':'https://example.com/draft'}):
                        self.tick_job(jid)
                    result=self.a.post(self.url+'/execution/jobs',json={'kind':kind,'resource_id':pub['id']})
                    self.assertEqual(result.status_code,200,result.text)
                    jid=result.json()['id']
                with server.db() as c:
                    content=server.resource(c,self.pid,pub['content_id'],'content')
                    content['channels']=['知乎']
                    server.put(c,self.pid,'content',content,content['id'])
                result=self.a.post(self.url+'/execution/jobs',json={'kind':kind,'resource_id':pub['id']})
                self.assertEqual(result.status_code,409,result.text)
                with patch.object(runtime,'request_json') as remote:
                    with self.assertRaises(runtime.AdapterError): self.tick_job(jid)
                    remote.assert_not_called()
                with server.db() as c:
                    self.assertEqual(server.resource(c,self.pid,pub['id'],'publication')['status'],'wp_draft' if kind=='wp_publish' else 'awaiting_connector')

    def test_wordpress_reconcile_stale_source_or_removed_channel_keeps_evidence_only(self):
        for reason in ('source','channel'):
            with self.subTest(reason=reason):
                pub,jid=self.publication_fixture()
                with server.db() as c:
                    job=server.resource(c,self.pid,jid,'execution');job['status']='unknown'
                    server.put(c,self.pid,'execution',job,jid)
                    content=server.resource(c,self.pid,pub['content_id'],'content')
                    if reason=='source':
                        doc=server.resource(c,self.pid,self.kid,'knowledge');doc['version']+=1
                        server.put(c,self.pid,'knowledge',doc,self.kid)
                    else:
                        content['channels']=['知乎']
                        server.put(c,self.pid,'content',content,content['id'])
                reconcile=self.a.post(self.url+'/execution/jobs/'+jid+'/action',json={'action':'reconcile'})
                self.assertEqual(reconcile.status_code,200,reconcile.text)
                rendered=''.join('<p>'+runtime.html.escape(x).replace('\n','<br>')+'</p>' for x in pub['body_snapshot'].split('\n\n'))
                remote=[{'id':101,'status':'publish','title':{'raw':pub['title']},'content':{'raw':rendered},'link':'https://example.com/old'}]
                with patch.object(runtime,'request_json',return_value=remote) as call:
                    result=self.tick_job(reconcile.json()['id'])
                    self.assertTrue(result.get('requires_attention'))
                    self.assertEqual(call.call_count,1)
                    self.assertEqual(call.call_args.args[1],'GET')
                state=self.a.get(self.url+'/state').json()
                saved=next(x for x in state['publication'] if x['id']==pub['id'])
                self.assertEqual(saved['status'],'awaiting_connector')
                self.assertEqual(saved['remote_evidence']['platform_status'],'publish')
                self.assertEqual(self.a.get(self.url+'/metrics').json()['published'],0)

    def test_manual_receipt_rejects_running_or_unknown_wordpress(self):
        pub, jid = self.publication_fixture()
        for status in ('running', 'unknown'):
            with self.subTest(status=status):
                with server.db() as c:
                    job = server.resource(c, self.pid, jid, 'execution')
                    job['status'] = status
                    server.put(c, self.pid, 'execution', job, jid)
                response = self.a.post(self.url + '/publications/' + pub['id'] + '/receipt', json={'url': 'https://example.com/manual'})
                self.assertEqual(response.status_code, 409, response.text)
                state = self.a.get(self.url + '/state').json()
                self.assertEqual(next(p for p in state['publication'] if p['id'] == pub['id'])['status'], 'awaiting_connector')
                self.assertEqual(next(j for j in state['execution'] if j['id'] == jid)['status'], status)

    def test_pdf_pages_and_unconfirmed_gate(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter(); page = writer.add_blank_page(width=500, height=500)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 20 450 Td (Product A: operating pressure 10 MPa.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        out = io.BytesIO(); writer.write(out)
        aid = self.a.post(self.url + '/assets?filename=product.pdf', content=out.getvalue()).json()['id']
        jid = self.a.post(self.url + '/execution/jobs', json={'kind': 'pdf', 'resource_id': aid}).json()['id']
        result = self.tick_job(jid)
        knowledge = next(k for k in self.a.get(self.url + '/state').json()['knowledge'] if k['id'] == result['knowledge_id'])
        self.assertEqual(knowledge['status'], 'pending')
        self.assertIn('10 MPa', knowledge['body'])
        self.assertEqual(knowledge['provenance']['pages'][0]['page'], 1)
        self.assertEqual(self.b.post(self.url + '/execution/jobs', json={'kind': 'pdf', 'resource_id': aid}).status_code, 404)

    def test_ssrf_and_quality_rules(self):
        for url in ['http://example.com', 'https://u:p@example.com', 'https://127.0.0.1', 'https://[::1]', 'https://169.254.169.254']:
            with self.assertRaises(runtime.AdapterError): runtime.public_target(url)
        with patch.object(runtime.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('10.0.0.1', 443))]):
            with self.assertRaises(runtime.AdapterError): runtime.public_target('https://public-looking.example')
        report = runtime.quality_report('保证通过，压力 100MPa [9]', [{'body': '压力 10MPa'}])
        self.assertEqual(report['status'], 'needs_review'); self.assertGreaterEqual(len(report['warnings']), 3)

    def test_geo_api_not_in_app_metrics_and_eval_has_no_key(self):
        self.configure(); before = self.a.get(self.url + '/metrics').json()['samples']
        job = self.a.post(self.url + '/execution/jobs', json={'kind': 'geo_api', 'question': '采购时考虑哪些技术条件？'}).json()
        with patch.object(runtime, 'request_json', return_value={'choices': [{'message': {'content': '应确认技术条件。'}}]}):
            self.tick_job(job['id'])
        s = self.a.get(self.url + '/state').json()
        self.assertEqual(s['observation'][0]['surface'], 'model_api')
        self.assertEqual(s['stats']['samples'], before)
        export = self.a.get(self.url + '/execution/promptfoo')
        self.assertEqual(export.status_code, 200, export.text)
        self.assertNotIn('private-test-secret', export.text)
        self.assertTrue(export.json()['tests'])

    def test_opengeo_brand_mismatch_and_website_audit(self):
        brand = '11111111-1111-4111-8111-111111111111'
        prompt = '22222222-2222-4222-8222-222222222222'
        r = self.a.post(self.url + '/execution/connectors', json={'kind': 'opengeo', 'endpoint': 'https://example.com/api/v1', 'external_brand_id': brand, 'secret': 'test'})
        self.assertEqual(r.status_code, 200, r.text)
        job = self.a.post(self.url + '/execution/jobs', json={'kind': 'geo_snapshot', 'resource_id': prompt, 'start_date': '2026-10-01', 'end_date': '2026-10-02'}).json()
        snapshot = {'brandId': 'another-brand', 'promptId': prompt, 'mentions': {}, 'citations': {}}
        with patch.object(runtime, 'request_json', return_value=snapshot):
            with self.assertRaises(runtime.AdapterError): self.tick_job(job['id'])
        self.assertEqual(self.a.get(self.url + '/state').json()['geo_snapshot'], [])
        snapshot['brandId'] = brand
        with patch.object(runtime, 'request_json', return_value=snapshot): self.tick_job(job['id'])
        self.assertEqual(len(self.a.get(self.url + '/state').json()['geo_snapshot']), 1)
        webjob = self.a.post(self.url + '/execution/jobs', json={'kind': 'website', 'url': 'https://example.com/product'}).json()
        with patch.object(runtime, 'request_bytes', return_value=(b'<html><title>Product guide</title><h1>Pressure</h1><p>Pressure 10 MPa with specific operating conditions.</p></html>', 'text/html', 'https://example.com/product')):
            self.tick_job(webjob['id'])
        state = self.a.get(self.url + '/state').json()
        self.assertEqual(len(state['seo_audit']), 1)
        self.assertEqual(state['knowledge'][0]['status'], 'pending')

    def test_wordpress_invalid_receipt_id_stays_unknown_and_blocks_resubmission(self):
        pub,jid=self.publication_fixture()
        for invalid_id in (True,0,-1,'101'):
            with self.subTest(invalid_id=invalid_id):
                with patch.object(runtime,'request_json',return_value={'id':invalid_id,'status':'draft','link':'https://example.com/draft'}):
                    with self.assertRaises(runtime.AdapterError): self.tick_job(jid)
        with patch.object(runtime,'request_json',return_value={'id':101,'status':'draft','link':'https://example.com/draft'}):
            self.tick_job(jid)
        published=self.a.post(self.url+'/execution/jobs',json={'kind':'wp_publish','resource_id':pub['id']}).json()['id']
        with server.db() as c:
            for row in c.execute('SELECT id,project_id FROM resources WHERE kind="execution"').fetchall():
                if row['id']!=published:
                    job=server.resource(c,row['project_id'],row['id'],'execution');job['status']='succeeded'
                    server.put(c,row['project_id'],'execution',job,job['id'])
        with patch.object(runtime,'request_json',return_value={'id':999,'status':'publish','link':'https://example.com/wrong'}) as remote:
            server.delivery['tick']()
            self.assertEqual(remote.call_count,1)
        with server.db() as c:
            saved=server.resource(c,self.pid,pub['id'],'publication')
            self.assertEqual(saved['status'],'wp_draft')
            self.assertEqual(saved['external_id'],101)
            self.assertEqual(server.resource(c,self.pid,published,'execution')['status'],'unknown')
        self.assertEqual(self.a.get(self.url+'/metrics').json()['published'],0)
        self.assertEqual(self.a.post(self.url+'/execution/jobs',json={'kind':'wp_publish','resource_id':pub['id']}).status_code,409)
        self.assertEqual(self.a.post(self.url+'/execution/jobs/'+published+'/action',json={'action':'retry'}).status_code,409)

    def test_wordpress_reconcile_rejects_wrong_or_invalid_remote_id(self):
        pub,jid=self.publication_fixture()
        with server.db() as c:
            p=server.resource(c,self.pid,pub['id'],'publication');p['external_id']=101
            server.put(c,self.pid,'publication',p,p['id'])
            j=server.resource(c,self.pid,jid,'execution');j['status']='unknown'
            server.put(c,self.pid,'execution',j,jid)
        reconcile=self.a.post(self.url+'/execution/jobs/'+jid+'/action',json={'action':'reconcile'}).json()['id']
        rendered=''.join('<p>'+runtime.html.escape(x).replace('\n','<br>')+'</p>' for x in pub['body_snapshot'].split('\n\n'))
        for remote_id in (999,True,0,-1):
            with self.subTest(remote_id=remote_id):
                result={'id':remote_id,'status':'publish','title':{'raw':pub['title']},'content':{'raw':rendered},'link':'https://example.com/wrong'}
                with patch.object(runtime,'request_json',return_value=result) as remote:
                    with self.assertRaises(runtime.AdapterError): self.tick_job(reconcile)
                    self.assertEqual(remote.call_args.args[1],'GET')
                with server.db() as c:
                    self.assertEqual(server.resource(c,self.pid,jid,'execution')['status'],'unknown')
                    self.assertEqual(server.resource(c,self.pid,pub['id'],'publication')['status'],'awaiting_connector')

    def test_wordpress_receipt_save_failure_recovers_by_read_only_reconcile(self):
        pub,jid=self.publication_fixture()
        with server.db() as c:
            for row in c.execute('SELECT id,project_id FROM resources WHERE kind="execution"').fetchall():
                if row['id']!=jid:
                    job=server.resource(c,row['project_id'],row['id'],'execution');job['status']='succeeded'
                    server.put(c,row['project_id'],'execution',job,job['id'])
            # Fault injection in the isolated test DB only; rollback the receipt update.
            c.execute("CREATE TRIGGER fail_test_receipt BEFORE UPDATE ON resources WHEN NEW.kind='publication' AND json_extract(NEW.data,'$.status')='wp_draft' BEGIN SELECT RAISE(ABORT,'simulated receipt storage failure'); END")
        try:
            with patch.object(runtime,'request_json',return_value={'id':101,'status':'draft','link':'https://example.com/draft'}) as remote:
                server.delivery['tick']()
                self.assertEqual(remote.call_count,1)
            with server.db() as c:
                self.assertEqual(server.resource(c,self.pid,jid,'execution')['status'],'unknown')
                self.assertEqual(server.resource(c,self.pid,pub['id'],'publication')['status'],'awaiting_connector')
            self.assertEqual(self.a.post(self.url+'/execution/jobs',json={'kind':'wp_draft','resource_id':pub['id']}).status_code,409)
        finally:
            with server.db() as c: c.execute('DROP TRIGGER fail_test_receipt')
        rec=self.a.post(self.url+'/execution/jobs/'+jid+'/action',json={'action':'reconcile'}).json()['id']
        rendered=''.join('<p>'+runtime.html.escape(x).replace('\n','<br>')+'</p>' for x in pub['body_snapshot'].split('\n\n'))
        remote=[{'id':101,'status':'draft','title':{'raw':pub['title']},'content':{'raw':rendered},'link':'https://example.com/draft'}]
        with patch.object(runtime,'request_json',return_value=remote) as call:
            self.tick_job(rec)
            self.assertEqual(call.call_count,1)
            self.assertEqual(call.call_args.args[1],'GET')
        with server.db() as c:
            self.assertEqual(server.resource(c,self.pid,jid,'execution')['status'],'reconciled')
            self.assertEqual(server.resource(c,self.pid,pub['id'],'publication')['external_id'],101)

    def test_worker_failure_is_persisted_without_secret(self):
        self.configure(); data = self.generate(True)
        # Keep this test focused: older fixture jobs are not run by this worker tick.
        with server.db() as c:
            for row in c.execute('SELECT id,project_id FROM resources WHERE kind="execution"').fetchall():
                if row['id'] != data['job_id']:
                    j=server.resource(c,row['project_id'],row['id'],'execution');j['status']='succeeded';server.put(c,row['project_id'],'execution',j,j['id'])
        with patch.object(runtime, 'request_json', side_effect=ValueError('private-test-secret')):
            server.delivery['tick']()
        s = self.a.get(self.url + '/state').json()
        job = next(x for x in s['execution'] if x['id'] == data['job_id'])
        self.assertEqual(job['status'], 'failed')
        self.assertNotIn('private-test-secret', job['error'])
        content = next(x for x in s['content'] if x['id'] == data['id'])
        self.assertEqual(content['status'], 'draft')
        self.assertEqual(self.a.post(self.url + '/contents/' + data['id'] + '/review', json={'revision': 1, 'action': 'submit'}).status_code, 409)


if __name__ == '__main__': unittest.main()
