"""Real authorized local model, fictional inputs, no customer or external writes."""
import json
from pathlib import Path
from unittest.mock import patch
import codex_local
import editorial_methods

if __name__ == '__main__':
    import sys
    if '--run-real' not in sys.argv:
        raise SystemExit('Pass --run-real explicitly')
    root = Path(__file__).parent
    tenant = 'a46fb911b04fbf0b783c7bf5'
    ready = codex_local.availability(root / '.runtime', tenant)
    if not ready['available']:
        raise SystemExit(ready['reason'])
    import test_format_skills as fixture
    case = fixture.FormatSkillTests('runTest')
    case.setUp(); case.configure()
    records=[]
    for mode in ('baseline', 'updated'):
        for fmt in ('article', 'moments'):
            body=dict(kind='expert_chat',workflow='repurpose',core_topic='盐雾500小时是否等于户外使用五年',
                      repurpose_channel=fmt,question='虚构练习：企业没有测试报告。写一份面向采购的短稿，最多350字，不虚构性能数据。',draft_reference=True)
            jid=case.a.post(case.url+'/execution/jobs',json=body).json()['id']
            if mode=='baseline':
                with fixture.server.db() as c:
                    job=fixture.server.resource(c,case.pid,jid,'execution')
                    p=job['payload'];p['prompt_snapshot']=p['prompt_snapshot'].split('\n工业内容论证方法')[0]
                    p['format_skill_snapshot'].pop('method',None)
                    fixture.server.put(c,case.pid,'execution',job,jid)
            def bridge(url,*args,**kwargs):
                if url!='https://example.com/v1/chat/completions':raise RuntimeError('Unexpected transport')
                answer,usage=codex_local.generate(root/'.runtime',tenant,'gpt-6-sol',kwargs['data']['messages'])
                return {'choices':[{'message':{'content':answer}}]}
            with patch.object(fixture.runtime,'request_json',side_effect=bridge):
                result=case.tick_job(jid)
            records.append(dict(mode=mode,format=fmt,answer=result['answer']))
            (root/'outputs/iteration86-editorial-real.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            print(mode,fmt,'complete',flush=True)
