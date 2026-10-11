import concurrent.futures,html,json,re,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:return r.read().decode('utf-8')
def weread(pair):
    bid,link=pair
    try:
        raw=read(link['url'])
        title=html.unescape(re.search(r'<title>(.*?)</title>',raw,re.S)[1])
        match=re.search(r'<meta name="description" content="(.*?)"',raw,re.S)
        description=html.unescape(match[1]) if match else ''
        return bid,{'type':'book_platform','title':title,'url':link['url'],'description':description,'checked':'2026-10-06','public_only':True}
    except Exception as e:return bid,{'error':str(e),'url':link['url']}
TOPICS={
'aging':'TITLE:"Hallmarks of Aging: An Expanding Universe"',
'exercise-brain':'DOI:10.1073/pnas.1015950108',
'meditation':'DOI:10.1001/jamainternmed.2013.13018',
'microbiome-diet':'DOI:10.1016/j.cell.2021.06.019',
'calorie-restriction':'DOI:10.1038/s43587-022-00357-y',
'synthetic-biology':'TITLE:"Synthetic biology" AND REVIEW:Y AND FIRST_PDATE:[2020-01-01 TO 2025-12-31]',
'circadian':'TITLE:"Circadian rhythms" AND REVIEW:Y AND FIRST_PDATE:[2022-01-01 TO 2025-12-31]',
'epigenetics':'TITLE:"Epigenetics and aging" AND REVIEW:Y',
'metabolism':'TITLE:"Insulin resistance" AND REVIEW:Y AND FIRST_PDATE:[2023-01-01 TO 2025-12-31]',
'inflammation':'TITLE:"Inflammaging" AND REVIEW:Y AND FIRST_PDATE:[2022-01-01 TO 2025-12-31]',
'microbiome-aging':'TITLE:"Gut microbiota and aging" AND REVIEW:Y',
'skin':'TITLE:"Skin barrier" AND REVIEW:Y AND FIRST_PDATE:[2022-01-01 TO 2025-12-31]',
'cancer-prevention':'TITLE:"Cancer prevention" AND REVIEW:Y AND FIRST_PDATE:[2023-01-01 TO 2025-12-31]',
'wellbeing':'TITLE:"Positive psychology interventions" AND TITLE:"meta-analysis"',
'ai-health':'TITLE:"Artificial intelligence" AND TITLE:"aging" AND REVIEW:Y',
}
def paper(pair):
    key,query=pair
    url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urllib.parse.urlencode({'query':query,'format':'json','resultType':'core','pageSize':2})
    try:
        data=json.loads(read(url));return key,{'query_url':url,'checked':'2026-10-06','records':[{'title':r.get('title'),'authors':r.get('authorString'),'year':r.get('pubYear'),'doi':r.get('doi'),'url':('https://doi.org/'+r['doi']) if r.get('doi') else 'https://europepmc.org/article/'+r['source']+'/'+r['id'],'abstract':re.sub('<[^>]*>',' ',r.get('abstractText','')),'publication_types':r.get('pubTypeList',{}).get('pubType',[])} for r in data.get('resultList',{}).get('result',[])]}
    except Exception as e:return key,{'error':str(e)}
if __name__=='__main__':
    links=json.loads((ROOT/'output/book-weread-research.json').read_text('utf-8'))
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        result=dict(pool.map(weread,[(k,v) for k,v in links.items() if v.get('verified')]))
    (ROOT/'output/book-public-weread.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WeRead',len(result),'usable',sum(bool(v.get('description')) for v in result.values()),flush=True)
    with concurrent.futures.ThreadPoolExecutor(3) as pool:result=dict(pool.map(paper,TOPICS.items()))
    (ROOT/'output/book-public-papers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Research',len(result),'usable',sum(bool(v.get('records')) for v in result.values()),flush=True)
