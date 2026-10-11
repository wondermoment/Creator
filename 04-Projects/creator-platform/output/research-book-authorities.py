import concurrent.futures,html,json,re,urllib.request
from pathlib import Path
URLS={
'physical-activity':'https://www.who.int/news-room/fact-sheets/detail/physical-activity',
'healthy-diet':'https://www.who.int/news-room/fact-sheets/detail/healthy-diet',
'aging-health':'https://www.who.int/news-room/fact-sheets/detail/ageing-and-health',
'meditation-safety':'https://www.nccih.nih.gov/health/meditation-and-mindfulness-effectiveness-and-safety',
'probiotics':'https://www.nccih.nih.gov/health/probiotics-what-do-we-know',
'genes':'https://medlineplus.gov/genetics/understanding/basics/gene/',
'dna':'https://medlineplus.gov/genetics/understanding/basics/dna/',
'epigenetics':'https://medlineplus.gov/genetics/understanding/howgeneswork/epigenome/',
'noncoding':'https://medlineplus.gov/genetics/understanding/basics/noncodingdna/',
'cells':'https://medlineplus.gov/genetics/understanding/basics/cell/',
'endocrine':'https://medlineplus.gov/endocrinediseases.html',
'telomere-nobel':'https://www.nobelprize.org/prizes/medicine/2009/summary/',
'enzyme-nobel':'https://www.nobelprize.org/prizes/chemistry/1946/summary/',
'chinese-medicine':'https://www.nccih.nih.gov/health/traditional-chinese-medicine-what-you-need-to-know',
'cancer-prevention':'https://www.cancer.gov/about-cancer/causes-prevention',
'synthetic-biology':'https://www.genome.gov/about-genomics/policy-issues/Synthetic-Biology',
'circadian':'https://www.nigms.nih.gov/education/fact-sheets/Pages/circadian-rhythms.aspx',
'outlive-publisher':'https://www.penguinrandomhouse.com/books/705161/outlive-by-peter-attia-md-with-bill-gifford/',
'ageless-author':'https://andrewsteele.co.uk/ageless/',
'greger-author':'https://nutritionfacts.org/book/how-not-to-age/',
}
def retrieve(pair):
 key,url=pair
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=25) as r:raw=r.read().decode('utf-8');final=r.url
  title=re.search('<title[^>]*>(.*?)</title>',raw,re.S|re.I)
  text=re.sub(r'<(script|style)\b[^>]*>[\s\S]*?</\1>',' ',raw,flags=re.I)
  text=html.unescape(re.sub('<[^>]*>',' ',text));text=re.sub(r'\s+',' ',text)
  return key,{'title':html.unescape(title[1]) if title else key,'url':final,'checked':'2026-10-06','text':text}
 except Exception as e:return key,{'url':url,'error':str(e)}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(4) as pool:results=dict(pool.map(retrieve,URLS.items()))
 Path('output/book-public-authorities.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 for k,v in results.items():print(k,'OK' if v.get('text') else v.get('error'),flush=True)
