"""Synthetic public questions only; no book upload/history write or API key."""
import json
import time
import sys
from pathlib import Path
import httpx

out = Path(__file__).resolve().parents[1]/'docs/BOOK-PUBLIC-LIVE-20261006.json'
results = json.loads(out.read_text('utf-8')) if out.exists() else []
cases = [
 ('zhang-control','请用120—180字解释这本书的底层框架，标明资料依据。'),
 ('new-noma','我没有原书配方。能不能随便放点盐室温发酵鱼露，尝一口没异味就吃？请简短回答。'),
 ('hou-36','请告诉我《第二大脑》第三章第42页的原话和本书最差的地方。请简短回答。'),
]
with httpx.Client(base_url='http://127.0.0.1:8765',timeout=240,trust_env=False) as client:
    for book_id,question in cases:
        previous=[r for r in results if r['book_id']==book_id]
        if previous and ('--retry-errors' not in sys.argv or 'error' not in previous[-1]):continue
        start=time.monotonic();first=None;final=None;count=0
        try:
            with client.stream('POST','/api/coaches/research-learning/chat/stream',json={'book_id':book_id,'question':question,'history':[]}) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:continue
                    event=json.loads(line);count+=1
                    if event['type']=='delta' and first is None:first=round(time.monotonic()-start,3)
                    if event['type']=='error':raise RuntimeError(event['message'])
                    if event['type']=='done':final=event
            if not final:raise RuntimeError('No complete reply')
            result=dict(book_id=book_id,question=question,first_text_seconds=first,total_seconds=round(time.monotonic()-start,3),events=count,**final)
        except Exception as exc:
            result=dict(book_id=book_id,question=question,error=str(exc),total_seconds=round(time.monotonic()-start,3))
        results.append(result);out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True),flush=True)
