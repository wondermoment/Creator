"""Opt-in real model check with fictional fixture; never writes customer records."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import codex_local

if __name__ == '__main__':
    replay = '--replay-saved' in sys.argv
    if '--run-real' not in sys.argv and not replay: raise SystemExit('Pass --run-real or --replay-saved explicitly')
    root=Path(__file__).parent;tenant='a46fb911b04fbf0b783c7bf5'
    ready=codex_local.availability(root/'.runtime',tenant)
    if not ready['available']:raise SystemExit(ready['reason'])
    import test_expert_workbench as fixture
    case=fixture.ExpertWorkbenchTests('runTest');case.setUp();case.configure()
    out=root/'outputs/iteration107';out.mkdir(parents=True,exist_ok=True)
    metas=[]
    def bridge(url,*args,**kwargs):
        if url!='https://example.com/v1/chat/completions':raise RuntimeError('Unexpected target')
        if replay:
            saved=json.loads((out/f'real-{len(metas)+1}.json').read_text(encoding='utf-8'))
            answer,meta=saved['result']['answer'],saved['meta']
        else:
            answer,meta=codex_local.generate(root/'.runtime',tenant,'gpt-6-sol',kwargs['data']['messages'])
        metas.append(meta)
        return {'model':meta['model'],'choices':[{'message':{'content':answer}}]}
    original=None
    for index,question in enumerate([
        '虚构演练：采购第一次找精密加工供应商，需要准备哪些资料？结合本次示例资料写完整公众号文章，避免广告口号，不编造案例或性能参数。',
        '只把开头改成采购常见沟通场景，结尾改成三条可执行准备事项。保留中间正文和事实边界，输出完整新版，不添加新参数。']):
        r=case.create(question=question,chat_brief={'audience':'初次采购精密加工的负责人','channel':'公众号','tone':'直白、具体，少用术语','length':'约600字'},revise_job_id=original['id'] if original else '')
        assert r.status_code==200,r.text
        job=case.job(r.json()['id'])
        with patch.object(fixture.runtime,'request_json',side_effect=bridge):result=case.tick_job(job['id'])
        assert result.get('answer') and not result.get('discarded'),result
        job.update(status='succeeded',result=result)
        with fixture.server.db() as c:fixture.server.put(c,case.pid,'execution',job,job['id'])
        if not replay:(out/f'real-{index+1}.json').write_text(json.dumps({'question':question,'result':result,'meta':metas[-1]},ensure_ascii=False,indent=2),encoding='utf-8')
        if original:assert case.job(original['id'])==original
        else:original=case.job(job['id'])  # Compare against committed updated timestamp.
        print(f'{"Saved-output replay" if replay else "Real model"} turn {index+1} completed',flush=True)
    # Persist only the fictional demo fixture for UI verification. Disable model
    # connectivity: browser checks must not inadvertently issue further calls.
    with fixture.server.db() as c:
        for connector in fixture.server.items(c,case.pid,'connector'):
            connector['enabled']=False
            connector['model']=''
            fixture.server.put(c,case.pid,'connector',connector,connector['id'])
        import sqlite3
        folder=root/'.runtime/iteration107-ui';folder.mkdir(parents=True,exist_ok=True)
        c.commit()
        with sqlite3.connect(folder/'test.db') as dest:c.backup(dest)
    (out/'verification.json').write_text(json.dumps({'real_model':'gpt-6-sol','turns':2,'fixture_only':True,'original_preserved':True,'verification_replays_saved_outputs':replay,'publications':0,'project':case.pid},ensure_ascii=False,indent=2),encoding='utf-8')
