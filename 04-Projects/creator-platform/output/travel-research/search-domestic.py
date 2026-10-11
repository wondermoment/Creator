import requests,json,concurrent.futures
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import quote
queries={'dali':'大理 文旅 洱海 生态廊道 喜洲 沙村','songyang':'松阳 文旅 陈家铺 松庄 杨家堂 攻略','xiapu':'霞浦 文旅 东壁 北岐 三沙 旅游','bama':'巴马 文旅 百魔洞 命河 旅游','longhushan':'龙虎山 文旅 泸溪河 上清古镇 旅游','jingmai':'景迈山 文旅 糯干 翁基 古茶林','wuyishan':'武夷山 文旅 九曲溪 天游峰 岩骨花香','qingcheng':'青城山 都江堰 文旅 前山 后山 攻略'}
def run(pair):
 k,q=pair;u='https://www.bing.com/search?q='+quote(q)
 try:
  r=requests.get(u,timeout=25);s=BeautifulSoup(r.content,'html.parser');rows=[]
  for li in s.select('li.b_algo')[:4]:
   a=li.select_one('h2 a')
   if a:rows.append({'title':a.get_text(' ',strip=True),'url':a['href'],'snippet':li.get_text(' ',strip=True)})
  Path('output/travel-research/'+k+'-search.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');return k,rows[:2]
 except Exception as e:return k,str(e)
for x in concurrent.futures.ThreadPoolExecutor(3).map(run,queries.items()):print(json.dumps(x,ensure_ascii=True))
