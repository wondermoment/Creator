import requests,concurrent.futures,json
from bs4 import BeautifulSoup
from pathlib import Path
sources={'dali':'https://en.wikivoyage.org/wiki/Dali','longhushan':'https://whc.unesco.org/en/list/1335/','songyang':'https://en.wikipedia.org/wiki/Songyang_County','jingmai':'https://whc.unesco.org/en/list/1665/','xiapu':'https://en.wikipedia.org/wiki/Xiapu_County','wuyishan':'https://whc.unesco.org/en/list/911/','qingcheng':'https://whc.unesco.org/en/list/1001/','bama':'https://en.wikipedia.org/wiki/Bama_Yao_Autonomous_County'}
def run(item):
 k,u=item
 try:
  r=requests.get(u,timeout=25); soup=BeautifulSoup(r.content,'html.parser')
  for e in soup(['script','style','nav','footer']):e.decompose()
  t=soup.get_text(' ',strip=True);Path('output/travel-research/'+k+'-verified.json').write_text(json.dumps({'url':u,'status':r.status_code,'text':t},ensure_ascii=False),encoding='utf-8')
  pos=t.find('Description') if 'unesco' in u else 0
  return k,r.status_code,t[max(pos,0):max(pos,0)+2000]
 except Exception as e:return k,str(e)
for r in concurrent.futures.ThreadPoolExecutor(8).map(run,sources.items()):print(r)
