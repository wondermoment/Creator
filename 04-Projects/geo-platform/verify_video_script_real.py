"""One authorized real text call with fictional inputs; isolated app fixture only."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import codex_local

if __name__ == '__main__':
    if '--run-real' not in sys.argv:
        raise SystemExit('Pass --run-real explicitly')
    root=Path(__file__).parent
    tenant='a46fb911b04fbf0b783c7bf5'
    ready=codex_local.availability(root/'.runtime',tenant)
    if not ready['available']:
        raise SystemExit(ready['reason'])
    import test_format_skills as fixture
    case=fixture.FormatSkillTests('runTest');case.setUp();case.configure()
    body=dict(kind='expert_chat',workflow='repurpose',core_topic='采购如何核对精密加工图纸与验收要求',
              repurpose_channel='short_video',question='虚构练习：面向采购人员，使用示例企业知识，制作60秒短视频脚本。没有实拍素材或测试报告，不编造性能数据，按默认分镜表格式输出。',draft_reference=True)
    response=case.a.post(case.url+'/execution/jobs',json=body)
    assert response.status_code==200,response.text
    jid=response.json()['id'];usage={}
    def bridge(url,*args,**kwargs):
        if url!='https://example.com/v1/chat/completions':raise RuntimeError('Unexpected transport')
        answer,meta=codex_local.generate(root/'.runtime',tenant,'gpt-6-sol',kwargs['data']['messages'])
        usage.update(meta)
        return {'model':meta['model'],'choices':[{'message':{'content':answer}}]}
    with patch.object(fixture.runtime,'request_json',side_effect=bridge):
        case.complete(jid)
    with fixture.server.db() as c:
        job=fixture.server.resource(c,case.pid,jid,'execution')
    saved=case.a.post(case.url+'/repurpose/from-job/'+jid,json={})
    assert saved.status_code==200,saved.text
    with fixture.server.db() as c:
        source=fixture.server.resource(c,case.pid,saved.json()['id'],'content')
    dest=root/'outputs/iteration106';dest.mkdir(parents=True,exist_ok=True)
    (dest/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'model-meta.json').write_text(json.dumps(usage,ensure_ascii=False,indent=2),encoding='utf-8')
    code="const fs=require('fs'),vm=require('vm');const c=vm.createContext({source:JSON.parse(fs.readFileSync(process.argv[1],'utf8'))});vm.runInContext(fs.readFileSync('static/video-script.js','utf8'),c);process.stdout.write(JSON.stringify(vm.runInContext('videoScriptScenes(source)',c)));"
    parsed=subprocess.run(['node','-e',code,str(dest/'source.json')],cwd=root,capture_output=True,text=True,encoding='utf-8')
    if parsed.returncode:
        (dest/'parse-error.txt').write_text(parsed.stderr,encoding='utf-8')
        raise SystemExit('Real output saved; script import failed; inspect parse-error.txt')
    scenes=json.loads(parsed.stdout)
    plan=case.a.post(case.url+'/video-composer/plans',json={'source_id':source['id'],'source_revision':source['revision'],
        'title':source['title'][:60],'engine':'remotion','aspect':'portrait','scenes':scenes})
    assert plan.status_code==200,plan.text
    (dest/'plan.json').write_text(json.dumps(plan.json(),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'real_model':usage['model'],'saved_draft':True,'scene_count':len(scenes),
                      'seconds':sum(s['seconds'] for s in scenes),'video_rendered':False}))
