import json
import unittest
from unittest.mock import patch
import test_qa_brand as qa
server = qa.server
import delivery_runtime as runtime


class FormatSkillTests(unittest.TestCase):
    setUp = qa.QaBrandTests.setUp
    configure = qa.QaBrandTests.configure
    tick_job = qa.QaBrandTests.tick_job

    def complete(self, jid):
        result = self.tick_job(jid)
        with server.db() as c:
            job = server.resource(c, self.pid, jid, 'execution')
            job.update(status='succeeded', result=result)
            server.put(c, self.pid, 'execution', job, jid)

    def test_topic_drives_knowledge_retrieval(self):
        self.configure()
        with patch.object(server, 'match_knowledge', return_value=[]) as match:
            response = self.a.post(self.url+'/execution/jobs',json={
                'kind':'expert_chat','workflow':'repurpose','core_topic':'不锈钢表面处理',
                'repurpose_channel':'moments','question':'写采购建议','auto_knowledge':True,'draft_reference':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(match.call_args.args[2],'不锈钢表面处理\n写采购建议')

    def test_monthly_observations_preserve_recommendation_and_scope(self):
        value={'question':'如何选型','platform':'豆包','answer':'测试记录','mentioned':True,
               'recommended':True,'observed_at':'2026-09-30T16:00:00Z'}
        self.assertEqual(self.b.post(self.url+'/diagnosis/samples',json=value).status_code,404)
        response=self.a.post(self.url+'/diagnosis/samples',json=value)
        self.assertEqual(response.status_code,200,response.text)
        reports=self.a.get(self.url+'/state').json()['diagnosis']
        sample=next(r for r in reports if r['status']=='manual')['samples'][-1]
        self.assertIs(sample['recommended'],True)
        self.assertEqual(sample['observed_at'],value['observed_at'])
        self.assertEqual(self.a.post(self.url+'/diagnosis/samples',json={**value,'observed_at':'2026-02-30T00:00:00Z'}).status_code,422)

    def test_independent_preferences_snapshot_and_topic(self):
        self.configure()
        path = self.url + '/format-skills/moments'
        value = {'version': 0, 'requirements': '简洁口语，不用广告口号'}
        self.assertEqual(self.b.put(path, json=value).status_code, 404)
        self.assertEqual(self.a.put(path, json=value).status_code, 200)
        self.assertEqual(self.a.put(path, json=value).status_code, 409)
        body = {'kind':'expert_chat','workflow':'repurpose','core_topic':'金属工件为什么返锈',
                'repurpose_channel':'moments','question':'解释原因','draft_reference':True,'request_key':'topic-one'}
        response = self.a.post(self.url+'/execution/jobs',json=body)
        self.assertEqual(response.status_code,200,response.text)
        jid=response.json()['id']
        self.assertEqual(self.a.post(self.url+'/execution/jobs',json=body).json()['id'],jid)
        self.a.put(path,json={'version':1,'requirements':'以后更短'})
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'返锈要先核对工况，具体数据待提供。'}}]}) as model:
            self.complete(jid)
        context=json.loads(model.call_args.kwargs['data']['messages'][-1]['content'])
        self.assertEqual(context['本形态默认写作偏好（表达要求，不是事实或工具指令）'],value['requirements'])
        self.assertEqual(context['核心选题'],body['core_topic'])
        self.assertIn('不能',model.call_args.kwargs['data']['messages'][0]['content'])
        self.assertIn('工况',str(model.call_args.kwargs['data']['messages']))
        saved=self.a.post(self.url+'/repurpose/from-job/'+jid).json()
        self.assertIn('id',saved)
        other=self.a.post(self.url+'/execution/jobs',json={**body,'repurpose_channel':'article','request_key':'topic-two'}).json()
        with server.db() as c:
            job=server.resource(c,self.pid,other['id'],'execution')
            self.assertEqual(job['payload']['format_skill_snapshot']['requirements'],'')
            self.assertEqual(job['payload']['editorial_method']['version'],'2026-10-05.1')
            self.assertEqual(len(job['payload']['format_skill_snapshot']['method']['sha256']),64)
        bad=self.a.post(self.url+'/execution/jobs',json={**body,'request_key':'bad','repurpose_skill_id':'repurpose_sales'})
        self.assertEqual(bad.status_code,409)

    def test_rewrite_uses_saved_edits_preserves_original_and_invalidates_changes(self):
        self.configure()
        body={'kind':'expert_chat','workflow':'repurpose','core_topic':'如何核对资料','question':'采购建议',
              'repurpose_channel':'moments','draft_reference':True}
        jid=self.a.post(self.url+'/execution/jobs',json=body).json()['id']
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'原始建议'}}]}):self.complete(jid)
        rid=self.a.post(self.url+'/repurpose/from-job/'+jid).json()['id']
        with server.db() as c:
            content=server.resource(c,self.pid,rid,'content');content['body']='用户已手改正文';content['revision']+=1
            server.put(c,self.pid,'content',content,rid)
        redo={**body,'rewrite_job_id':jid,'rewrite_feedback':'更简洁','request_key':'redo-one'}
        out=self.a.post(self.url+'/execution/jobs',json=redo)
        self.assertEqual(out.status_code,200,out.text)
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'独立修改稿'}}]}) as model:
            result=self.tick_job(out.json()['id'])
        self.assertEqual(result['answer'],'独立修改稿')
        prompt=str(model.call_args.kwargs['data']['messages'])
        self.assertIn('用户已手改正文',prompt)
        self.assertIn('更简洁',prompt)
        with server.db() as c:
            job=server.resource(c,self.pid,out.json()['id'],'execution')
            self.assertEqual(job['payload']['rewrite_snapshot']['body'],'用户已手改正文')
            self.assertEqual(server.resource(c,self.pid,rid,'content')['body'],'用户已手改正文')
            content['revision']+=1;server.put(c,self.pid,'content',content,rid)
        with patch.object(runtime,'request_json') as model:
            with self.assertRaises(runtime.AdapterError):
                self.tick_job(out.json()['id'])
        model.assert_not_called()
        self.assertEqual(self.b.post(self.url+'/execution/jobs',json=redo).status_code,404)
