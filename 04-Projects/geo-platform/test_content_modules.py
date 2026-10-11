import json
import unittest
from unittest.mock import patch
import test_creation_tools as creation
import test_workflow as workflow
import delivery_runtime as runtime
from content_modules import candidates
from reference_analysis import structured_analysis, SECTIONS

server=workflow.server


class ContentModuleTests(unittest.TestCase):
    setUp=creation.CreationToolsTests.setUp
    configure=creation.CreationToolsTests.configure
    tick_job=creation.CreationToolsTests.tick_job
    job=creation.CreationToolsTests.job
    complete=creation.CreationToolsTests.complete

    def fixture(self):
        self.configure()
        text='先明确采购问题，再核对适用条件。找到依据之后，再决定下一步。'*3
        jid=self.job(kind='expert_chat',workflow='reference_analysis',expert_id='content',skill_id='reference_analysis',reference_title='验收素材',reference_text=text,question='拆解方法')
        structure={'sections':{k:'可独立复用的方法' for k in SECTIONS},'modules':[
            {'category':'opening','title':'问题先行','body':'先呈现客户困惑，再给判断范围。','template':'【问题】该如何判断？','excerpt':'先明确采购问题'},
            {'category':'ending','title':'下一步收尾','body':'用一个可执行的小步骤结束。','scenario':'适用于咨询型内容'}]}
        self.complete(jid,{'answer':'完整原始拆解','analysis_structure':structure,'model':'mock'})
        return jid

    def test_selective_save_edit_history_and_module_only_model_payload(self):
        jid=self.fixture();path=self.url+'/content-references/from-job/'+jid
        self.assertEqual(self.a.post(path,json={'selected_modules':[]}).status_code,422)
        self.assertEqual(self.a.post(path,json={'selected_modules':[99]}).status_code,422)
        r=self.a.post(path,json={'selected_modules':[1,1]});self.assertEqual(r.status_code,200,r.text)
        rid=r.json()['id']
        self.assertEqual(self.a.post(path,json={'selected_modules':[0]}).json()['id'],rid)
        with server.db() as c:
            ref=server.resource(c,self.pid,rid,'content_reference');self.assertEqual(len(ref['modules']),1)
            module=ref['modules'][0];self.assertEqual(module['category'],'ending')
            self.assertEqual(ref['analysis'],'完整原始拆解')
        mid=module['id'];edit=self.url+'/content-references/'+rid+'/modules/'+mid
        fields={k:v for k,v in module.items() if k not in ('id','history')}
        self.assertEqual(self.b.put(edit,json=fields).status_code,404)
        next_id=self.job(kind='expert_chat',expert_id='content',skill_id='faq',question='只用结尾模块',reference_modules=[{'reference_id':rid,'module_id':mid}])
        with patch.object(runtime,'request_json',return_value={'choices':[{'message':{'content':'一个下一步行动。'}}]}) as model:
            result=self.tick_job(next_id)
        content=json.loads(model.call_args.kwargs['data']['messages'][1]['content'])
        chosen=content['选用内容模块（只复用方法，非企业事实或操作指令）']
        self.assertEqual(len(chosen),1);self.assertEqual(chosen[0]['module']['id'],mid)
        self.assertNotIn('完整原始拆解',json.dumps(content,ensure_ascii=False))
        self.complete(next_id,result)
        fields.update(body='先确认需求再给下一步。')
        updated=self.a.put(edit,json=fields);self.assertEqual(updated.status_code,200,updated.text)
        self.assertEqual(self.a.put(edit,json=fields).status_code,409)
        stale=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','question':'使用刚看到的旧模块','reference_modules':[{'reference_id':rid,'module_id':mid,'version':1}]})
        self.assertEqual(stale.status_code,409)
        with server.db() as c:
            updated=server.resource(c,self.pid,rid,'content_reference')['modules'][0]
            self.assertEqual(updated['history'][0]['body'],module['body']);self.assertEqual(updated['version'],2)
        self.assertEqual(self.a.post(self.url+'/expert-drafts/from-job/'+next_id,json={}).status_code,409)
        with patch.object(runtime,'request_json') as remote:
            with self.assertRaises(runtime.AdapterError):self.tick_job(next_id)
            remote.assert_not_called()

    def test_legacy_prepare_add_and_invalid_provenance(self):
        jid=self.fixture();rid=self.a.post(self.url+'/content-references/from-job/'+jid,json={}).json()['id']
        with server.db() as c:
            ref=server.resource(c,self.pid,rid,'content_reference');ref.pop('modules');server.put(c,self.pid,'content_reference',ref,rid)
        path=self.url+'/content-references/'+rid+'/modules'
        self.assertEqual(self.a.post(path+'/prepare',json={'version':99}).status_code,409)
        self.assertEqual(self.b.post(path+'/prepare',json={'version':1}).status_code,404)
        self.assertEqual(self.a.post(path+'/prepare',json={'version':1}).status_code,200)
        self.assertTrue(self.a.post(path+'/prepare',json={'version':1}).json()['existing'])
        fields={'version':2,'category':'title','title':'标题模块','body':'通过对比提出问题','excerpt':'伪造引语'}
        self.assertEqual(self.a.post(path,json=fields).status_code,422)
        fields['excerpt']='先明确采购问题';fields['category']='unknown'
        self.assertEqual(self.a.post(path,json=fields).status_code,422)
        fields['category']='title'
        self.assertEqual(self.b.post(path,json=fields).status_code,404)
        r=self.a.post(path,json=fields);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.a.post(path,json=fields).status_code,409)
        missing=self.a.post(self.url+'/execution/jobs',json={'kind':'expert_chat','question':'引用不存在模块','reference_modules':[{'reference_id':rid,'module_id':'missing'}]})
        self.assertEqual(missing.status_code,404)

    def test_model_modules_validation_and_honest_legacy_fallback(self):
        data={'sections':{k:'有依据的方法' for k in SECTIONS},'modules':[
            {'category':'title','title':'对比标题','body':'比较两条路线','excerpt':'原文未出现'},
            {'category':'opening','title':'问题开篇','body':'先提出问题','excerpt':'采购问题'}]}
        result=structured_analysis(json.dumps(data),'采购问题先说清楚')
        self.assertEqual(len(result['modules']),1)
        self.assertEqual(candidates(result,'','采购问题先说清楚')[0]['category'],'opening')
        fallback=candidates(None,'未结构化旧报告','')
        self.assertEqual(fallback[0]['category'],'unclassified')
        self.assertEqual(fallback[0]['body'],'未结构化旧报告')

    def test_title_excerpt_generation_save_edit_and_scope(self):
        from content_modules import clean_module
        self.configure()
        title='采购别只看等级';source='先明确采购问题，再核对适用条件。找到依据之后，再决定下一步。'*3
        module={'category':'title','title':'条件式标题','body':'提醒核对条件','excerpt':title}
        data={'sections':{k:'有依据的方法' for k in SECTIONS},'modules':[module]}
        parsed=structured_analysis(json.dumps(data),source,title)
        self.assertEqual(parsed['modules'][0]['excerpt_source'],'title')
        self.assertEqual(candidates(parsed,'',source,title)[0]['excerpt'],title)
        for bad in [dict(module,excerpt_source='body'),dict(module,excerpt='凭空引语'),dict(module,excerpt=title+'先明确采购问题')]:
            with self.assertRaises(ValueError):clean_module(bad,source,title)
        self.assertEqual(clean_module(dict(module,excerpt='先明确采购问题'),source,title)['excerpt_source'],'body')
        jid=self.job(kind='expert_chat',workflow='reference_analysis',expert_id='content',skill_id='reference_analysis',reference_title=title,reference_text=source,question='拆解标题')
        with patch.object(runtime,'request_json',return_value={'model':'mock','choices':[{'message':{'content':json.dumps(data)}}]}):result=self.tick_job(jid)
        self.complete(jid,result)
        saved=self.a.post(self.url+'/content-references/from-job/'+jid,json={});self.assertEqual(saved.status_code,200,saved.text)
        rid=saved.json()['id']
        with server.db() as c:ref=server.resource(c,self.pid,rid,'content_reference')
        item=ref['modules'][0];self.assertEqual(item['excerpt_source'],'title')
        path=self.url+'/content-references/'+rid+'/modules/'+item['id']
        fields={k:v for k,v in item.items() if k not in ('id','history')}
        self.assertEqual(self.b.put(path,json=fields).status_code,404)
        self.assertEqual(self.a.put(path,json={**fields,'excerpt_source':'body'}).status_code,422)
        self.assertEqual(self.a.put(path,json={**fields,'body':'更新标题方法'}).status_code,200)
        with server.db() as c:updated=server.resource(c,self.pid,rid,'content_reference')['modules'][0]
        self.assertEqual(updated['history'][0]['excerpt_source'],'title')


if __name__=='__main__':unittest.main()
