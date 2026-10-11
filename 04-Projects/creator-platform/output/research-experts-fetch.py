import urllib.request,urllib.parse,json,concurrent.futures
from pathlib import Path
queries={'barzilai':'TITLE:"Metformin as a Tool to Target Aging"','longo':'TITLE:"Fasting-mimicking diet and markers/risk factors"','sinclair':'TITLE:"Reprogramming to recover youthful epigenetic information"','attia':'TITLE:"Outlive"'}
urls={'sinclair-lab':'https://sinclair.hms.harvard.edu/','longo-site':'https://valterlongo.com/','attia-book':'https://peterattiamd.com/outlive/','attia-blog':'https://peterattiamd.com/category/exercise/','barzilai-book':'https://us.macmillan.com/books/9781250230854/','sinclair-book':'https://www.simonandschuster.com/books/Lifespan/David-A-Sinclair/9781501191978'}
Path('output/research-experts').mkdir(exist_ok=True)
def fetch(item):
 key,url=item
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=30) as r: body=r.read().decode('utf-8','replace');final=r.url
  Path('output/research-experts/'+key+'.txt').write_text(body,encoding='utf-8');return {'id':key,'url':url,'final':final,'bytes':len(body)}
 except Exception as e:return {'id':key,'url':url,'error':str(e)}
for key,q in queries.items(): urls[key+'-paper']='https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=core&query='+urllib.parse.quote(q)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(fetch,urls.items()))
Path('output/research-experts/fetch-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results))
