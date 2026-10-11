from pathlib import Path
import requests,json,sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
sources={
 'amh':'https://medlineplus.gov/lab-tests/anti-mullerian-hormone-test/',
 'vitamin-d':'https://medlineplus.gov/lab-tests/vitamin-d-test/'
}
for key,url in sources.items():
 existing=Path(f'output/testing-hormone-{key}-source-20261005.json')
 if existing.exists():
  print(key,existing.read_text('utf-8'))
  continue
 r=requests.get(url,timeout=35)
 soup=BeautifulSoup(r.content,'html.parser')
 main=soup.find('article') or soup.find('main') or soup
 for tag in main(['script','style','nav','footer']):tag.decompose()
 result=dict(url=url,status=r.status_code,text=main.get_text(' ',strip=True))
 Path(f'output/testing-hormone-{key}-source-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(key,r.status_code,result['text'][:24000])
