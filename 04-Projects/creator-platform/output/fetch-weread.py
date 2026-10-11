import requests,json,concurrent.futures,re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import quote
books=json.loads(Path('output/weread-books.json').read_text(encoding='utf-8'));out=Path('output/weread');out.mkdir(exist_ok=True)
def fetch(b):
 u='https://weread.qq.com/web/search/books?keyword='+quote(b['title'])
 try:
  r=requests.get(u,timeout=30);s=BeautifulSoup(r.content.decode('utf-8'),'html.parser');rows=[]
  for li in s.select('li.wr_bookList_item'):
   a=li.select_one('a.wr_bookList_item_link');t=li.select_one('.wr_bookList_item_title');au=li.select_one('.wr_bookList_item_author')
   if a and t:rows.append({'title':t.get_text(strip=True),'author':au.get_text(strip=True) if au else '', 'url':'https://weread.qq.com'+a['href']})
  result={'book':b,'status':r.status_code,'search':u,'results':rows};(out/(b['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return b['id'],len(rows)
 except Exception as e:return b['id'],str(e)
for x in concurrent.futures.ThreadPoolExecutor(3).map(fetch,books):print(x,flush=True)
