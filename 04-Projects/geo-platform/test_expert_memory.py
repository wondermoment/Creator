import json
import unittest
from unittest.mock import patch
from expert_memory import recall_requests
import test_qa_brand
import delivery_runtime as runtime
server = test_qa_brand.server


class ExpertMemoryTests(unittest.TestCase):
    setUp = test_qa_brand.QaBrandTests.setUp
    configure = test_qa_brand.QaBrandTests.configure
    tick_job = test_qa_brand.QaBrandTests.tick_job

    def test_long_term_recall_and_actor_boundary(self):
        def row(i, text, actor='a'):
            return {'id': str(i), 'actor': actor, 'job_type': 'expert_chat',
                    'status': 'succeeded', 'payload': {'question': text, 'expert_id': 'content'}}
        jobs = [row(i, '普通需求') for i in range(50)]
        jobs += [row(50, '以后统一使用专业简洁的风格'), row(51, '船舶涂装需突出工况'), row(52, '船舶机密', 'b')]
        result = recall_requests(jobs, 'a', '船舶文章提纲')
        self.assertIn('50', [r['job_id'] for r in result])
        self.assertIn('51', [r['job_id'] for r in result])
        self.assertNotIn('52', [r['job_id'] for r in result])
        self.assertLessEqual(len(result), 24)

    def test_cross_expert_requests_reach_model_and_tenant_isolation(self):
        self.configure()
        body = {'kind': 'expert_chat', 'expert_id': 'content', 'skill_id': 'faq',
                'question': '以后文章面向采购负责人，保持简洁，不要夸大。'}
        first = self.a.post(self.url+'/execution/jobs', json=body)
        self.assertEqual(first.status_code, 200, first.text)
        body.update(expert_id='technical', question='请延续我之前要求的风格')
        second = self.a.post(self.url+'/execution/jobs', json=body)
        self.assertEqual(second.status_code, 200, second.text)
        # Unauthorized tenants cannot even create the memory-consuming job.
        self.assertEqual(self.b.post(self.url+'/execution/jobs', json=body).status_code, 404)
        with patch.object(runtime, 'request_json', return_value={
                'choices': [{'message': {'content': '面向采购负责人撰写建议。'}}]}) as model:
            self.tick_job(second.json()['id'])
        context = json.loads(model.call_args.kwargs['data']['messages'][1]['content'])
        memory = context['跨专家需求记忆（非事实依据）']
        self.assertEqual(memory[0]['job_id'], first.json()['id'])
        self.assertEqual(memory[0]['expert_id'], 'content')
        self.assertIn('采购负责人', memory[0]['request'])
        self.assertNotIn('answer', memory[0])

    def method_conversation(self, module=False):
        self.configure()
        with server.db() as c:
            ref=server.put(c,self.pid,'content_reference',{'title':'采购表达','analysis':'先条件后证据','version':1,'tags':'','note':'',
                'source_sha256':'fixture','modules':[{'id':'opening','version':1,'template':'先说明适用条件'}]})
        def turn(question,refs=()):
            response=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','expert_id':'content',
                'skill_id':'faq','question':question,'reference_ids':list(refs) if not module else [],
                'reference_modules':[{'reference_id':ref,'module_id':'opening','version':1}] if module and refs else [],'auto_knowledge':False})
            self.assertEqual(response.status_code,200,response.text)
            jid=response.json()['id']
            with server.db() as c:
                job=server.resource(c,self.pid,jid,'execution')
                job.update(status='succeeded',result={'answer':'模拟建议：'+question,'model':'mock'})
                server.put(c,self.pid,'execution',job,jid)
            return jid
        first=turn('用所选方法给采购建议',[ref])
        second=turn('延续刚才的建议')
        third=turn('基于前两轮完善')
        return ref,first,second,third

    def change_method(self,rid):
        with server.db() as c:
            ref=server.resource(c,self.pid,rid,'content_reference');ref['version']+=1
            server.put(c,self.pid,'content_reference',ref,rid)

    def queue_again(self,jid):
        with server.db() as c:
            job=server.resource(c,self.pid,jid,'execution');job['status']='queued'
            server.put(c,self.pid,'execution',job,jid)

    def test_conversation_method_changes_block_call_and_saved_draft(self):
        ref,_,second,third=self.method_conversation()
        saved=self.a.post(self.url+'/expert-drafts/from-job/'+third,json={})
        self.assertEqual(saved.status_code,200,saved.text)
        self.change_method(ref)
        self.queue_again(second)
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'不应生成'}}]}) as remote:
            with self.assertRaises(runtime.AdapterError):self.tick_job(second)
            remote.assert_not_called()
        self.assertEqual(self.a.post(self.url+'/expert-drafts/from-job/'+third,json={}).status_code,409)
        cid=saved.json()['id']
        self.assertEqual(self.a.post(self.url+'/contents/'+cid+'/review',json={'revision':1,'action':'submit'}).status_code,409)

    def test_conversation_method_changes_remove_stale_answers_but_keep_user_requests(self):
        ref,_,_,_=self.method_conversation();self.change_method(ref)
        r=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','expert_id':'content','skill_id':'faq',
                                                     'question':'继续给建议','auto_knowledge':False})
        self.assertEqual(r.status_code,200,r.text)
        with server.db() as c:
            payload=server.resource(c,self.pid,r.json()['id'],'execution')['payload']
        self.assertEqual(payload['history'],[])
        self.assertTrue(payload['shared_memory'],'user requests remain context, not method evidence')

    def test_conversation_method_change_during_model_discards_answer(self):
        ref,_,_,third=self.method_conversation()
        self.queue_again(third)
        def response(*args,**kwargs):
            self.change_method(ref)
            return {'choices':[{'message':{'content':'模拟在途回复'}}]}
        with patch.object(runtime,'request_json',side_effect=response):result=self.tick_job(third)
        self.assertTrue(result.get('discarded'),result)
        self.assertNotIn('answer',result)

    def test_selected_module_versions_follow_conversation(self):
        ref,_,_,third=self.method_conversation(module=True)
        self.queue_again(third)
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'有效方法建议'}}]}):
            self.assertEqual(self.tick_job(third)['answer'],'有效方法建议')
        with server.db() as c:
            source=server.resource(c,self.pid,ref,'content_reference')
            source['modules'][0]['version']+=1
            server.put(c,self.pid,'content_reference',source,ref)
        with patch.object(runtime,'request_json') as remote:
            with self.assertRaises(runtime.AdapterError):self.tick_job(third)
            remote.assert_not_called()

    def test_legacy_history_without_method_trail_is_not_reused(self):
        _,_,second,third=self.method_conversation()
        with server.db() as c:
            for jid in (second,third):
                job=server.resource(c,self.pid,jid,'execution')
                job['payload'].pop('history_methods')
                server.put(c,self.pid,'execution',job,jid)
        r=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','expert_id':'content',
            'skill_id':'faq','question':'继续建议','auto_knowledge':False})
        self.assertEqual(r.status_code,200,r.text)
        with server.db() as c:
            history=server.resource(c,self.pid,r.json()['id'],'execution')['payload']['history']
        self.assertEqual([x['question'] for x in history],['用所选方法给采购建议'])


if __name__ == '__main__':
    unittest.main()
