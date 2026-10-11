"""Explicit opt-in real-model acceptance; uses isolated fixture data only."""
import argparse
import json
from pathlib import Path
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-real', action='store_true')
    args = parser.parse_args()
    if not args.run_real:
        parser.error('Real model usage requires --run-real')
    import codex_local
    runtime_dir = Path(__file__).parent / '.runtime'
    authorized_project = 'a46fb911b04fbf0b783c7bf5'
    ready = codex_local.availability(runtime_dir, authorized_project)
    if not ready['available']:
        raise RuntimeError(ready['reason'])
    # This import selects a temporary DB before importing server.
    import test_expert_memory as fixture
    case = fixture.ExpertMemoryTests('runTest')
    case.setUp()
    case.configure()
    records = []
    output = Path(__file__).parent / 'outputs' / 'iteration69-real-memory.json'
    turns = [
        ('content', '隔离验收：以后所有建议统一使用两条编号，每条不超过20字，不用感叹号。只确认你记住的表达偏好，不写企业事实。'),
        ('technical', '这是虚构练习。请按我之前的表达偏好，给采购沟通建议；不引用企业事实。'),
        ('strategist', '更正之前的偏好：以后改为三条编号，每条不超过15字；旧的两条要求作废。只用新格式确认，不写企业事实。'),
        ('video', '这是虚构练习。按我最新的表达偏好，给拍摄产品演示的准备建议，不写企业事实。'),
    ]
    for expert, question in turns:
        started = time.monotonic()
        response = case.a.post(case.url+'/execution/jobs', json={
            'kind':'expert_chat','expert_id':expert,'skill_id':'faq','question':question,
            'auto_knowledge':False,'knowledge_ids':[]})
        response.raise_for_status()
        jid = response.json()['id']
        with fixture.server.db() as c:
            queued = fixture.server.resource(c, case.pid, jid, 'execution')
        transport = {}
        def bridge(url, *args, **kwargs):
            if url != 'https://example.com/v1/chat/completions':
                raise RuntimeError('Unexpected test transport')
            answer, usage = codex_local.generate(runtime_dir, authorized_project, 'gpt-6-sol', kwargs['data']['messages'])
            transport.update(usage)
            return {'choices':[{'message':{'content':answer}}], 'usage':usage['usage']}
        try:
            with patch.object(fixture.runtime, 'request_json', side_effect=bridge):
                result = case.tick_job(jid)
            result.update(transport)  # Do not report fixture API prices as real costs.
            with fixture.server.db() as c:
                job = fixture.server.resource(c, case.pid, jid, 'execution')
                job.update(status='succeeded', result=result)
                fixture.server.put(c, case.pid, 'execution', job, jid)
            record = {'expert':expert,'question':question,'seconds':round(time.monotonic()-started,2),
                      'memory':queued['payload']['shared_memory'],'result':result}
        except Exception as exc:
            record = {'expert':expert,'error':str(exc),'seconds':round(time.monotonic()-started,2)}
        records.append(record)
        output.write_text(json.dumps({'mode':'isolated fixture with real authorized Codex transport',
            'production_scheduler_tested':False,'turns':records},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False), flush=True)
        if 'error' in record:
            raise RuntimeError(record['error'])


if __name__ == '__main__':
    main()
