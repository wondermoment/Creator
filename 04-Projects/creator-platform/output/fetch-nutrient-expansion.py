import json,urllib.request,urllib.parse,concurrent.futures
from pathlib import Path
root=Path('output/nutrient-expansion-sources');root.mkdir(exist_ok=True)
sources={'protein':'10.1136/bjsports-2017-097608','fiber':'10.1016/S0140-6736(18)31809-9','calcium':'10.1136/bmj.h4183','b12':'10.3945/ajcn.115.110775','magnesium':'10.3945/ajcn.114.085282','creatine':'10.2147/OAJSM.S123529'}
def fetch(item):
 key,doi=item
 url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urllib.parse.urlencode({'query':'DOI:'+doi,'format':'json','resultType':'core'})
 try:
  data=json.load(urllib.request.urlopen(url,timeout=40));(root/(key+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  r=data['resultList']['result'][0]
  return {'id':key,'doi':r.get('doi'),'title':r.get('title'),'journal':r.get('journalInfo'),'abstract':r.get('abstractText')}
 except Exception as e:return {'id':key,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for result in pool.map(fetch,sources.items()):print(json.dumps(result,ensure_ascii=False))
