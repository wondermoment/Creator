import json,time,urllib.request
from pathlib import Path
ctx=json.loads(Path('output/nutrient-live-context.json').read_text('utf-8'))['context']
q='合成测试案例：一位45岁女性每天服用左甲状腺素，看到补钙能抗衰的宣传，想早餐把钙片和药一起吃。你会怎样回应？请结合这篇研究讲清能证明什么、不能证明什么，不编造个体剂量。'
payload={'question':q,'history':[{'role':'user','content':ctx}]};t=time.monotonic()
try:
 req=urllib.request.Request('http://127.0.0.1:8765/api/coaches/nutrients/chat',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8765'},method='POST')
 with urllib.request.urlopen(req,timeout=300) as r: result={'seconds':round(time.monotonic()-t,2),'response':json.load(r)}
except Exception as e:result={'seconds':round(time.monotonic()-t,2),'error':str(e)}
result.update(question=q,context=ctx,synthetic=True)
Path('docs/NUTRIENT-LIVE-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
