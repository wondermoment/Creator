import json,time,urllib.request
from pathlib import Path
ctx=json.loads(Path('output/research-context-test.json').read_text('utf-8'))['context']
q='合成验证：Sinclair 的重编程研究是否已经证明人吃NMN可以恢复视力？请说明研究对象、干预和局限，附对应论文链接。'
payload={'question':q,'history':[{'role':'user','content':ctx}]};t=time.monotonic()
try:
 req=urllib.request.Request('http://127.0.0.1:8765/api/coaches/research-learning/chat',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8765'},method='POST')
 with urllib.request.urlopen(req,timeout=300) as r: result={'seconds':round(time.monotonic()-t,2),'response':json.load(r)}
except Exception as e:result={'seconds':round(time.monotonic()-t,2),'error':str(e)}
result['question']=q;result['context']=ctx
Path('docs/RESEARCH-KNOWLEDGE-LIVE-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
