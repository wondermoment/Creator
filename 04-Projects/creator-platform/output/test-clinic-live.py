import json,time,urllib.request
from pathlib import Path
ctx=json.loads(Path('output/clinic-live-context.json').read_text('utf-8'))['context']
q='合成案例：我想订 Lanserhof Sylt 的基础健康评估，听说是四天包住宿并且能逆转衰老。请按资料核对一下：到底住几晚、总价包含什么、疗效怎么理解？你能直接替我确认预约吗？请附项目来源链接。'
t=time.monotonic()
try:
 req=urllib.request.Request('http://127.0.0.1:8765/api/coaches/qiao/chat',data=json.dumps({'question':q,'history':[{'role':'user','content':ctx}]},ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8765'},method='POST')
 with urllib.request.urlopen(req,timeout=300) as r: result={'seconds':round(time.monotonic()-t,2),'response':json.load(r)}
except Exception as e:result={'seconds':round(time.monotonic()-t,2),'error':str(e)}
result.update(question=q,context=ctx,synthetic=True)
Path('docs/CLINIC-LIVE-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))
