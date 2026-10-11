import json
import unittest
from unittest.mock import patch
import test_qa_brand
import delivery_runtime as runtime
import expert_playbooks
server = test_qa_brand.server


class ExpertWorkbenchTests(unittest.TestCase):
    setUp = test_qa_brand.QaBrandTests.setUp
    configure = test_qa_brand.QaBrandTests.configure
    tick_job = test_qa_brand.QaBrandTests.tick_job

    def create(self, **kwargs):
        body = dict(kind='expert_chat', expert_id='content', question='写采购文章',
                    knowledge_ids=[self.kid], draft_reference=True)
        body.update(kwargs)
        return self.a.post(self.url+'/execution/jobs', json=body)

    def job(self, jid):
        with server.db() as c: return server.resource(c, self.pid, jid, 'execution')

    def completed(self, **kwargs):
        r = self.create(**kwargs); self.assertEqual(r.status_code, 200, r.text)
        job = self.job(r.json()['id'])
        job.update(status='succeeded', result={'answer': '指定的旧原文 [1]，保留条件。'})
        with server.db() as c: server.put(c, self.pid, 'execution', job, job['id'])
        return job

    def test_six_contracts_and_brief_reach_model(self):
        self.configure()
        for expert in expert_playbooks.ROLES:
            r = self.create(expert_id=expert, chat_brief={'audience':'采购负责人','tone':'直白','channel':'公众号','length':'800字'})
            self.assertEqual(r.status_code, 200, r.text)
            j = self.job(r.json()['id'])
            self.assertIn(expert_playbooks.ROLES[expert], j['payload']['prompt_snapshot'])
            with patch.object(runtime, 'request_json', return_value={'choices':[{'message':{'content':'模拟成果 [1]'}}]}) as model:
                self.tick_job(j['id'])
            text = json.dumps(model.call_args.kwargs['data']['messages'], ensure_ascii=False)
            self.assertIn('采购负责人', text)
            self.assertIn('800字', text)
            self.assertIn('本次写作要求', text)

    def test_exact_revision_preserves_original_and_citations(self):
        self.configure(); original = self.completed()
        # More recent unrelated replies must not replace an explicit older target.
        self.completed(question='另一条问题')
        r = self.create(question='缩短开篇，保留其他段落', revise_job_id=original['id'], auto_knowledge=True)
        self.assertEqual(r.status_code, 200, r.text)
        job = self.job(r.json()['id']); payload = job['payload']
        self.assertEqual(payload['chat_revision']['answer'], original['result']['answer'])
        self.assertEqual(payload['sources'], original['payload']['sources'])
        self.assertNotIn('model_sources', payload)
        with patch.object(runtime, 'request_json', return_value={'choices':[{'message':{'content':'改后正文 [1]'}}]}) as model:
            self.tick_job(job['id'])
        messages = model.call_args.kwargs['data']['messages']
        self.assertIn('指定的旧原文', messages[-1]['content'])
        self.assertEqual(self.job(original['id']), original)

    def test_wrong_expert_actor_tenant_and_flow_rejected(self):
        self.configure(); original = self.completed()
        self.assertEqual(self.create(expert_id='video', revise_job_id=original['id']).status_code, 409)
        self.assertEqual(self.create(workflow='repurpose', revise_job_id=original['id']).status_code, 422)
        self.assertEqual(self.b.post(self.url+'/execution/jobs', json={'kind':'expert_chat','question':'改','revise_job_id':original['id']}).status_code, 404)
        with server.db() as c:
            original['actor'] = 'someone-else';server.put(c, self.pid, 'execution', original, original['id'])
        self.assertEqual(self.create(revise_job_id=original['id']).status_code, 409)

    def test_source_change_before_and_during_revision(self):
        for moment in ('before', 'queued', 'inflight'):
            with self.subTest(moment=moment):
                self.setUp();self.configure();original = self.completed()
                def change():
                    with server.db() as c:
                        k=server.resource(c,self.pid,self.kid,'knowledge');k['version']+=1
                        server.put(c,self.pid,'knowledge',k,self.kid)
                if moment == 'before':
                    change();self.assertEqual(self.create(revise_job_id=original['id']).status_code,409);continue
                r=self.create(revise_job_id=original['id']);jid=r.json()['id']
                if moment == 'queued':
                    change()
                    with patch.object(runtime,'request_json') as model:
                        with self.assertRaises(runtime.AdapterError):self.tick_job(jid)
                        model.assert_not_called()
                else:
                    def answer(*args,**kwargs):
                        change();return {'choices':[{'message':{'content':'不得保留'}}]}
                    with patch.object(runtime,'request_json',side_effect=answer):result=self.tick_job(jid)
                    self.assertTrue(result['discarded']);self.assertNotIn('answer',result)

    def test_validation_and_other_workflows_unchanged(self):
        self.configure()
        self.assertEqual(self.create(chat_brief={'tone':'字'*161}).status_code,422)
        original=self.completed()
        with server.db() as c:
            original['result']['answer']='字'*20001;server.put(c,self.pid,'execution',original,original['id'])
        self.assertEqual(self.create(revise_job_id=original['id']).status_code,422)
        r=self.create(workflow='repurpose',repurpose_channel='article',core_topic='采购问题')
        self.assertEqual(r.status_code,200,r.text)
        self.assertNotIn('内容专家交付规范',self.job(r.json()['id'])['payload']['prompt_snapshot'])

    def test_article_draft_title_edit_preview_and_pending_review(self):
        self.configure(); original=self.completed()
        original['result']['answer']='# 采购图纸准备指南\n\n先确认图纸版本，再核对材料要求。[1]'
        with server.db() as c:server.put(c,self.pid,'execution',original,original['id'])
        r=self.a.post(self.url+'/expert-drafts/from-job/'+original['id'],json={})
        self.assertEqual(r.status_code,200,r.text);rid=r.json()['id']
        with server.db() as c:draft=server.resource(c,self.pid,rid,'content')
        self.assertEqual(draft['title'],'采购图纸准备指南')
        self.assertEqual(draft['body'],'先确认图纸版本，再核对材料要求。[1]')
        self.assertEqual(draft['status'],'draft')
        again=self.a.post(self.url+'/expert-drafts/from-job/'+original['id'],json={})
        self.assertEqual(again.json()['id'],rid)
        edited=self.a.put(self.url+'/contents/'+rid,json={'revision':1,'title':draft['title'],'body':draft['body']+'\n具体要求需确认。','channels':['微信公众号']})
        self.assertEqual(edited.status_code,200,edited.text)
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':2}).status_code,409)
        submitted=self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':2,'action':'submit'})
        self.assertEqual(submitted.status_code,200,submitted.text)
        state=self.a.get(self.url+'/state').json()
        pending=next(x for x in state['content'] if x['id']==rid)
        self.assertEqual(pending['status'],'pending')
        self.assertIsNone(pending['approved_revision'])
        self.assertEqual(state['publication'],[])
        self.assertEqual(self.job(original['id'])['result']['answer'],original['result']['answer'])


if __name__ == '__main__':unittest.main()
