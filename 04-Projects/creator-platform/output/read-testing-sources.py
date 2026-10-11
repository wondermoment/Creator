import json, urllib.request, concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
urls={
 'genetic':'https://medlineplus.gov/genetics/understanding/dtcgenetictesting/dtcrisksbenefits/',
 'gut':'https://www.nccih.nih.gov/health/probiotics-what-do-we-know',
 'oral':'https://www.nidcr.nih.gov/health-info/gum-disease',
 'nad':'https://ods.od.nih.gov/factsheets/Niacin-HealthProfessional/',
 'metabolic':'https://medlineplus.gov/metabolicdisorders.html',
 'chronic':'https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/',
 'immune':'https://medlineplus.gov/immunesystemanddisorders.html',
 'environment':'https://www.cdc.gov/biomonitoring/about/index.html',
 'elements':'https://medlineplus.gov/lab-tests/heavy-metal-blood-test/'
}
urls={
 'gut':'https://www.nccih.nih.gov/health/probiotics-usefulness-and-safety',
 'nad':'https://www.cancer.gov/publications/dictionaries/cancer-terms/def/nad',
 'environment':'https://www.niehs.nih.gov/health/topics/agents/endocrine'
}
def fetch(pair):
 key,url=pair
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:
   soup=BeautifulSoup(r.read(),'html.parser')
   for tag in soup(['script','style','nav','footer','header']):tag.decompose()
   body=soup.find('main') or soup.find(id='main') or soup
   result={'url':r.url,'status':r.status,'text':body.get_text(' ',strip=True)}
 except Exception as exc:result={'url':url,'error':str(exc)}
 Path(f'output/testing-remaining-{key}-source-20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return key,result.get('status'),result.get('text','')[:1400],result.get('error')
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for result in pool.map(fetch,urls.items()):print(json.dumps(result,ensure_ascii=False))
