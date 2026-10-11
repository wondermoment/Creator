import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app import local_codex as lc
original=lc.subprocess.run
trace=[]
def diagnostic(args,**kwargs):
    if 'exec' in args:
        opts=['model_provider="chatgpt_https"','model_providers.chatgpt_https.name="ChatGPT HTTPS"','model_providers.chatgpt_https.base_url="https://chatgpt.com/backend-api/codex"','model_providers.chatgpt_https.requires_openai_auth=true','model_providers.chatgpt_https.wire_api="responses"','model_providers.chatgpt_https.supports_websockets=false']
        args=args[:-1]+sum((['-c',x] for x in opts),[])+args[-1:]
    r=original(args,**kwargs)
    if 'exec' in args:
        trace.append({'returncode':r.returncode,'reconnecting':b'Reconnecting' in r.stderr,'websocket_fallback':b'Falling back from WebSockets' in r.stderr})
    return r
lc.subprocess.run=diagnostic
start=time.monotonic()
try:
    answer,meta=lc.generate('.runtime','synthetic',None,[{'role':'system','content':'你是中餐菜谱教练。用简短中文回应，一次只追问一个必要问题。'},{'role':'user','content':'帮我改良一道家常菜'}])
    result={'seconds':round(time.monotonic()-start,2),'answer':answer,'meta':meta,'trace':trace,'scope':'Synthetic question; isolated process transport options, no provider config file or real user data changes'}
except Exception as e:result={'seconds':round(time.monotonic()-start,2),'error':str(e),'trace':trace}
Path('docs/CHAT-HTTPS-DIAGNOSTIC-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
