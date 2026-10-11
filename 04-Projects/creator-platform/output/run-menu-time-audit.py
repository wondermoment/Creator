"""Serial, resumable real localhost model audit; synthetic inputs only, no app records."""
import json,time,sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
cases=json.loads((ROOT/'output/menu-time-cases-20261006.json').read_text('utf-8'))
out=ROOT/'docs/MENU-TIME-LIVE-20261006.json'
results=json.loads(out.read_text('utf-8')) if out.exists() else []
with httpx.Client(base_url='http://127.0.0.1:8765',timeout=240,trust_env=False) as client:
 for c in cases:
  if any(r['id']==c['id'] for r in results):continue
  history=[{'role':'user','content':c['context']}] if c.get('context') else []
  if c.get('previous'):
   prev=next((r for r in reversed(results) if r['id']==c['previous']),None)
   if not prev or not prev.get('answer'):continue
   history += [{'role':'user','content':prev['question']},{'role':'assistant','content':prev['answer'][:4000]}]
  body={'question':c['question'],'history':history}
  if c.get('book_id'):body['book_id']=c['book_id']
  start=time.monotonic();first=None;final=None;error=None;partial=''
  try:
   with client.stream('POST','/api/coaches/'+c['endpoint']+'/chat/stream',json=body) as r:
    r.raise_for_status()
    for line in r.iter_lines():
     if not line:continue
     event=json.loads(line)
     if event['type']=='delta':
      if first is None:first=round(time.monotonic()-start,3)
      partial+=event.get('text','')
     if event['type']=='error':raise RuntimeError(event['message'])
     if event['type']=='done':final=event
   if not final:raise RuntimeError('No done event')
  except Exception as exc:error=str(exc)
  result={**c,'first_text_seconds':first,'total_seconds':round(time.monotonic()-start,3),'review_status':'pending_ai_review',**(final or {}),**({'error':error,'partial_unaccepted':partial} if error else {})}
  results.append(result);out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'id':c['id'],'seconds':result['total_seconds'],'first':first,'error':error,'chars':len(result.get('answer',''))}),flush=True)
