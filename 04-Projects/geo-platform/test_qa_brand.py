import unittest
from unittest.mock import patch
import test_workflow as workflow
import test_delivery
import delivery_runtime as runtime
server=workflow.server

class QaBrandTests(unittest.TestCase):
 setUp=workflow.WorkflowTests.setUp
 configure=test_delivery.DeliveryTests.configure
 tick_job=test_delivery.DeliveryTests.tick_job

 def test_pending_lookup_and_draft_provenance(self):
  with server.db() as c:
   k=server.resource(c,self.pid,self.kid,'knowledge');k.update(status='pending',body='QATEST999 硅晶原始资料');server.put(c,self.pid,'knowledge',k,self.kid)
  self.assertFalse(self.a.post(self.url+'/knowledge-search',json={'query':'QATEST999'}).json()['matches'])
  r=self.a.post(self.url+'/knowledge-search',json={'query':'QATEST999','include_pending':True}).json()['matches'];self.assertEqual(r[0]['status'],'pending')
  self.assertEqual(self.b.post(self.url+'/knowledge-search',json={'query':'QATEST999','include_pending':True}).status_code,404)
  self.assertEqual(self.a.post(self.url+'/knowledge-search',json={'query':'   '}).status_code,422)
  data={'question':'硅晶如何应用？','answer':'引用原始资料待核准。','source_ids':[self.kid],'source_versions':{self.kid:k['version']},'draft_reference':True}
  r=self.a.post(self.url+'/faq',json=data);self.assertEqual(r.status_code,200,r.text)
  faq=next(f for f in self.a.get(self.url+'/state').json()['faq'] if f['id']==r.json()['id'])
  self.assertEqual(self.a.post(self.url+'/knowledge/'+faq['knowledge_id']+'/confirm',json={'version':1}).status_code,409)
  data['source_versions'][self.kid]+=1
  self.assertEqual(self.a.post(self.url+'/faq',json=data).status_code,409)

 def test_brand_section_versions_and_scope(self):
  old=self.a.get(self.url+'/state').json()['brand'];v=old[0]['version'] if old else 0
  r=self.a.put(self.url+'/brand/sections/company_intro',json={'value':'企业介绍全文','version':v});self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.a.put(self.url+'/brand/sections/company_intro',json={'value':'旧版覆盖','version':v}).status_code,409)
  self.assertEqual(self.b.put(self.url+'/brand/sections/company_intro',json={'value':'跨企业','version':v+1}).status_code,404)
  self.assertEqual(self.a.put(self.url+'/brand/sections/nope',json={'value':'bad','version':v+1}).status_code,422)
  self.a.put(self.url+'/brand/sections/voice',json={'value':'专业具体','version':v+1})
  brand=self.a.get(self.url+'/state').json()['brand'][0]
  self.assertEqual(brand['company_intro'],'企业介绍全文');self.assertEqual(brand['history'][-1]['fields']['company_intro'],'企业介绍全文')

 def test_expert_task_executes_and_core_config_denied(self):
  self.configure()
  with patch.object(server,'prompt_admin',return_value=False):
   self.assertEqual(self.a.get(self.url+'/admin-config').status_code,403)
   self.assertEqual(self.a.get(self.url+'/writing-reference').status_code,403)
   r=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','expert_id':'technical','skill_id':'faq','question':'图纸需要哪些资料？','auto_knowledge':True})
   self.assertEqual(r.status_code,200,r.text)
   with patch.object(runtime,'request_json',return_value={'model':'test-model','choices':[{'message':{'content':'请先提供图纸与工况 [1]。'}}],'usage':{'prompt_tokens':20,'completion_tokens':10}}):
    result=self.tick_job(r.json()['id'])
   self.assertIn('图纸',result['answer'])
   for path in ['/state','/execution','/manager','/export']:
    r=self.a.get(self.url+path);self.assertEqual(r.status_code,200,r.text)
    self.assertNotIn('"prompt_snapshot"',r.text);self.assertNotIn('"markdown"',r.text)
   self.assertNotIn('"prompt"',self.a.get('/api/me').text)

 def expert_job(self, sources=None):
  r=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','expert_id':'technical','skill_id':'faq','question':'继续整理采购问题','knowledge_ids':sources or [],'draft_reference':True})
  self.assertEqual(r.status_code,200,r.text)
  with server.db() as c:return server.resource(c,self.pid,r.json()['id'],'execution')

 def complete_expert(self, job, answer='原版采购建议'):
  with server.db() as c:
   job.update(status='succeeded',result={'answer':answer})
   server.put(c,self.pid,'execution',job,job['id'])

 def test_expert_history_filters_changed_sources_and_retains_audit(self):
  self.configure()
  first=self.expert_job([self.kid]);self.complete_expert(first)
  second=self.expert_job()
  self.assertEqual(second['payload']['history'][0]['answer'],'原版采购建议')
  self.assertEqual(second['payload']['history_sources'][0]['id'],self.kid)
  self.complete_expert(second,'引用前轮的建议')
  with server.db() as c:
   source=server.resource(c,self.pid,self.kid,'knowledge');source['version']+=1;source['body']='修订后的采购依据'
   server.put(c,self.pid,'knowledge',source,self.kid)
  third=self.expert_job()
  self.assertEqual(third['payload']['history'],[])
  with server.db() as c:self.assertEqual(server.resource(c,self.pid,first['id'],'execution')['result']['answer'],'原版采购建议')

 def test_expert_history_rechecks_queued_and_inflight_source_status(self):
  for moment in ('queued','inflight'):
   with self.subTest(moment=moment):
    self.setUp();self.configure()
    first=self.expert_job([self.kid]);self.complete_expert(first)
    second=self.expert_job()
    def downgrade():
     with server.db() as c:
      source=server.resource(c,self.pid,self.kid,'knowledge');source['status']='pending'
      server.put(c,self.pid,'knowledge',source,self.kid)
    if moment=='queued':
     downgrade()
     with patch.object(runtime,'request_json') as remote:
      with self.assertRaises(runtime.AdapterError):self.tick_job(second['id'])
      remote.assert_not_called()
    else:
     def response(*args,**kwargs):
      downgrade()
      return {'choices':[{'message':{'content':'不得复用旧依据的结论'}}],'usage':{'prompt_tokens':50,'completion_tokens':10}}
     with patch.object(runtime,'request_json',side_effect=response):result=self.tick_job(second['id'])
     self.assertTrue(result['discarded']);self.assertNotIn('answer',result)
     self.assertEqual(result['usage']['prompt_tokens'],50)

 def test_expert_legacy_history_without_provenance_is_not_reused(self):
  self.configure()
  first=self.expert_job()
  first['payload'].update(history=[{'question':'旧问题','answer':'旧结论'}])
  first['payload'].pop('history_sources')
  self.complete_expert(first)
  self.assertEqual(self.expert_job()['payload']['history'],[])

if __name__=='__main__':unittest.main()
