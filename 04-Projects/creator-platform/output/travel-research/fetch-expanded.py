import requests,bs4,json,concurrent.futures
from pathlib import Path
urls={'shaxi':'https://roamfun.cn/travel-guide/yunnan/yunnan-shaxi-old-town-guide/','sixsenses':'https://www.sixsenses.com/en/resorts/qing-cheng-mountain/','amanfayun':'https://www.aman.com/resorts/amanfayun','amanyangyun':'https://www.aman.com/resorts/amanyangyun','zulal':'https://zulal.com/','euphoria':'https://www.euphoriaretreat.com/','clp':'https://www.cliniquelaprairie.com/','lanserhof':'https://lanserhof.com/en/','sha':'https://shawellness.com/en/'}
def get(k,u):
 try:
  r=requests.get(u,timeout=25);r.encoding=r.apparent_encoding if 'charset' not in r.headers.get('Content-Type','') else r.encoding;s=bs4.BeautifulSoup(r.text,'html.parser');imgs=[{'src':x.get('src'),'alt':x.get('alt')} for x in s.select('img')];[x.decompose() for x in s(['script','style','nav','footer'])];d={'url':r.url,'status':r.status_code,'text':s.get_text(' ',strip=True),'images':imgs};Path('output/travel-research/'+k+'-expanded.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');return k,r.status_code,d['text'][:11000]
 except Exception as e:return k,str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for row in ex.map(lambda kv:get(*kv),urls.items()):print(json.dumps(row,ensure_ascii=True))
