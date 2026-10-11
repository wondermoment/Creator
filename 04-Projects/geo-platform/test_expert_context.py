import json
import unittest
from unittest.mock import patch
import test_creation_tools as creation
import delivery_runtime as runtime
from expert_context import project_sources

server=creation.server

class ContextSelectionTests(unittest.TestCase):
    setUp=creation.CreationToolsTests.setUp
    configure=creation.CreationToolsTests.configure
    tick_job=creation.CreationToolsTests.tick_job
    job=creation.CreationToolsTests.job

    def test_verbatim_neighbors_budget_and_stable_citations(self):
        body='前提：仅限指定基材。\n\n盐雾验证需核对试样。\n\n限制：不代表所有工况。\n\n'+('其他信息。'*80)
        sources=[{'id':'a','body':body,'version':4},{'id':'b','body':'无关内容。'*100,'version':1}]
        before=json.dumps(sources)
        projected,stats=project_sources(sources,'盐雾验证',budget=100)
        self.assertEqual([s['id'] for s in projected],['a','b'])
        self.assertLessEqual(stats['sent_chars'],100)
        self.assertEqual(len(projected[0]['excerpts']),3)
        for part in projected[0]['excerpts']:
            self.assertEqual(part['text'],body[part['start']:part['end']])
        self.assertIn('限制',projected[0]['excerpts'][-1]['text'])
        self.assertEqual(projected[1]['excerpts'],[])
        self.assertEqual(json.dumps(sources),before)
        long,_=project_sources([{'id':'c','body':'盐雾条件'*100,'version':1}],'盐雾',20)
        self.assertEqual(long[0]['excerpts'],[],'do not cut a large paragraph into a misleading fragment')

    def test_small_source_stays_complete(self):
        sources=[{'id':'a','body':'条件和限制不能丢失','version':1}]
        projected,stats=project_sources(sources,'条件')
        self.assertEqual(projected,sources);self.assertEqual(stats['mode'],'full')

    def test_model_projection_keeps_full_snapshot_and_stale_source_gate(self):
        self.configure()
        with server.db() as c:
            doc=server.resource(c,self.pid,self.kid,'knowledge')
            doc['body']='限定基材。\n\n盐雾采购条件。\n\n不得外推。\n\n'+('背景内容。'*3000)
            server.put(c,self.pid,'knowledge',doc,self.kid)
        jid=self.job(kind='expert_chat',question='盐雾采购条件',auto_knowledge=True)
        with server.db() as c:
            job=server.resource(c,self.pid,jid,'execution')
            self.assertEqual(job['payload']['sources'][0]['body'],doc['body'])
            self.assertEqual(job['payload']['context_selection']['mode'],'excerpts')
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'仅限提供条件。[1]'}}]}) as model:
            self.tick_job(jid)
        messages=model.call_args.kwargs['data']['messages']
        source=json.loads(messages[1]['content'])['当前核准资料'][0]
        self.assertEqual(source['序号'],1);self.assertEqual(source['body'],'')
        self.assertIn('不得外推',str(source['excerpts']));self.assertIn('未传全文',messages[0]['content'])
        with server.db() as c:
            doc['version']+=1;server.put(c,self.pid,'knowledge',doc,self.kid)
        with patch.object(runtime,'request_json') as remote:
            with self.assertRaises(runtime.AdapterError):self.tick_job(jid)
            remote.assert_not_called()
        explicit=self.job(kind='expert_chat',question='完整阅读资料',auto_knowledge=False,knowledge_ids=[self.kid])
        with server.db() as c:
            self.assertNotIn('model_sources',server.resource(c,self.pid,explicit,'execution')['payload'])

if __name__=='__main__':unittest.main()
