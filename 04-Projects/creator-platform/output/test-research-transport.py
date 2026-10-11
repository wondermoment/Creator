import sys,time,json,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'backend')
from app import local_codex
real_run=subprocess.run
trace=[]
def timed_run(args,*a,**kw):
 if 'exec' in args:
  args=args[:-1]+['-c','model_providers.openai.supports_websockets=false',args[-1]]
 started=time.monotonic();r=real_run(args,*a,**kw)
 if 'exec' in args:trace.append({'seconds':round(time.monotonic()-started,2),'stderr':r.stderr.decode('utf-8','replace')[-2500:]})
 return r
ctx=json.loads(Path('output/research-context-test.json').read_text('utf-8'))['context']
messages=[{'role':'system','content':'你是研究学习助手。只依据所附资料回答。明确研究对象及局限，附真实来源，不提供剂量，不声称本人身份。'},{'role':'user','content':ctx},{'role':'user','content':'Sinclair 的重编程研究是否已经证明人吃NMN可以恢复视力？请说明依据，给出对应论文链接。'}]
started=time.monotonic()
try:
 with patch.object(local_codex.subprocess,'run',side_effect=timed_run):answer,meta=local_codex.generate('.runtime','synthetic',None,messages)
 result={'seconds':round(time.monotonic()-started,2),'answer':answer,'meta':meta,'transport_override':'model_providers.openai.supports_websockets=false; diagnostic process only','trace':trace}
except Exception as e:result={'seconds':round(time.monotonic()-started,2),'error':str(e),'trace':trace}
Path('docs/RESEARCH-TRANSPORT-TEST-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
