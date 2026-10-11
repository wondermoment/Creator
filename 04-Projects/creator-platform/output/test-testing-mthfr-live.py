import json,time,urllib.request
from pathlib import Path
ctx=json.loads(Path('output/testing-mthfr-live-context.json').read_text('utf-8'))['context']
q='合成案例：一位准备怀孕的成年人拿到MTHFR 677TT结果，商家说她不能利用普通叶酸，必须停用医生原来的方案，改买高剂量甲基叶酸。这个结论成立吗？请依据提供资料解释，不给个体剂量，附来源链接。'
t=time.monotonic()
try:
 req=urllib.request.Request('http://127.0.0.1:8765/api/coaches/qiao/chat',data=json.dumps({'question':q,'history':[{'role':'user','content':ctx}]},ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8765'},method='POST')
 with urllib.request.urlopen(req,timeout=300) as r: result={'seconds':round(time.monotonic()-t,2),'response':json.load(r)}
except Exception as e:result={'seconds':round(time.monotonic()-t,2),'error':str(e)}
result.update(question=q,context=ctx,synthetic=True)
Path('docs/TESTING-MTHFR-LIVE-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
