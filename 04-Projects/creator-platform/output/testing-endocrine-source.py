from pathlib import Path
import requests,json,sys
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding='utf-8')
for key,url in {'cortisol':'https://medlineplus.gov/lab-tests/cortisol-test/','estrogen':'https://medlineplus.gov/lab-tests/estrogen-levels-test/'}.items():
 dest=Path(f'output/testing-endocrine-{key}-source-20261005.json')
 if dest.exists():
  result=json.loads(dest.read_text('utf-8'))
 else:
  r=requests.get(url,timeout=35)
  soup=BeautifulSoup(r.content,'html.parser');main=soup.find('article') or soup.find('main') or soup
  for tag in main(['script','style','nav','footer']):tag.decompose()
  result=dict(url=url,status=r.status_code,text=main.get_text(' ',strip=True))
  dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(key,result['status'],result['text'].split('References')[0])
